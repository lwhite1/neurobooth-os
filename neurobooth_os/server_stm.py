import socket
import sys
import os
from time import time, sleep
from collections import OrderedDict
from datetime import datetime
import copy 

import neurobooth_os
from neurobooth_os import config
from neurobooth_os.iout.screen_capture import ScreenMirror
from neurobooth_os.iout.lsl_streamer import start_lsl_threads, close_streams, reconnect_streams
from neurobooth_os.iout import metadator as meta

from neurobooth_os.netcomm import socket_message, get_client_messages, NewStdout, get_data_timeout

from neurobooth_os.tasks.wellcome_finish_screens import welcome_screen, finish_screen
import neurobooth_os.tasks.utils as utl
from neurobooth_os.tasks.task_importer import get_task_funcs


def Main():
    os.chdir(neurobooth_os.__path__[0])

    sys.stdout = NewStdout("STM",  target_node="control", terminal_print=True)
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    win = utl.make_win(full_screen=False)
    conn = meta.get_conn()

    streams, screen_running, presented = {}, False, False

    for data, connx in get_client_messages(s1):

        if "scr_stream" in data:
            if not screen_running:
                screen_feed = ScreenMirror()
                screen_feed.start()
                # print("Stim screen feed running")
                screen_running = True
            else:
                print(f"-OUTLETID-:Screen:{screen_feed.outlet_id}")
                print("Already running screen feed")

        elif "prepare" in data:
            # data = "prepare:collection_id:str(log_task_dict)"

            collection_id = data.split(":")[1]
            log_task = eval(data.replace(f"prepare:{collection_id}:", ""))
            subject_id_date = log_task["subject_id-date"]

            ses_folder = f"{config.paths['data_out']}{subject_id_date}"
            if not os.path.exists(ses_folder):
                os.mkdir(ses_folder)

            # delete subj_date as not present in DB
            del log_task["subject_id-date"]

            task_func_dict = get_task_funcs(collection_id, conn)
            task_devs_kw = meta._get_device_kwargs_by_task(collection_id, conn)

            if len(streams):
                print("Checking prepared devices")
                streams = reconnect_streams(streams)
            else:
                streams = start_lsl_threads("presentation", collection_id, win=win)

            print("UPDATOR:-Connect-")
            

        elif "present" in data:  # -> "present:TASKNAME:subj_id"
            # task_name can be list of task1-task2-task3
            
            tasks, subj_id = data.split(":")[1:]
            task_karg ={"win": win,
                        "path": config.paths['data_out'] + f"{subject_id_date}/",
                        "subj_id": subject_id_date,
                        "marker_outlet": streams['marker'],
                        }
            if streams.get('Eyelink'):
                    task_karg["eye_tracker"] = streams['Eyelink']
                    
            if presented:
                task_func_dict = get_task_funcs(collection_id, conn)
                
            # Preload tasks media
            for task in tasks.split("-"):
                if task not in task_func_dict.keys():
                    continue
                tsk_fun = copy.copy(task_func_dict[task]['obj'])
                this_task_kwargs = {**task_karg, **task_func_dict[task]['kwargs']}
                task_func_dict[task]['obj'] = tsk_fun(**this_task_kwargs)

            win = welcome_screen(with_audio=False, win=win)
            # When win is created, stdout pipe is reset
            if not hasattr(sys.stdout, 'terminal'):
                sys.stdout = NewStdout("STM",  target_node="control", terminal_print=True)
            
            tasks = tasks.split("-")
            task_calib = [t for t in tasks if 'calibration_task' in t]
            # Show calibration instruction video only the first time
            calib_instructions = True
            
            while len(tasks):
                task = tasks.pop(0)
                
                if task not in task_func_dict.keys():
                    print(f"Task {task} not implemented")
                    continue

                # get task and params
                tsk_fun = task_func_dict[task]['obj']
                this_task_kwargs = {**task_karg, **task_func_dict[task]['kwargs']}
                
                # Do not record if intro instructions"
                if "intro_" in task:
                    tsk_fun.run(**this_task_kwargs)
                    continue                    
                
                t_obs_id = task_func_dict[task]['t_obs_id']
                log_task_id = meta._make_new_tech_obs_row(conn, subj_id)
                log_task["date_times"] = '{'+ datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '}'
                tsk_strt_time = datetime.now().strftime("%Hh-%Mm-%Ss")

                # Signal CTR to start LSL rec
                print(f"Initiating task:{task}:{t_obs_id}:{log_task_id}:{tsk_strt_time}")
                sleep(1)

                # Start eyetracker if device in tech_obs 
                if streams.get('Eyelink') and any('Eyelink' in d for d in list(task_devs_kw[task])):
                    # if not streams['Eyelink'].calibrated:
                    #     streams['Eyelink'].calibrate()
                    fname = f"{config.paths['data_out']}{subject_id_date}/{subject_id_date}_{tsk_strt_time}_{t_obs_id}.edf"
                    
                    # if not calibration record with start method
                    if 'calibration_task' in task:
                        this_task_kwargs.update({"fname": fname, "instructions":calib_instructions})
                    else:
                        streams['Eyelink'].start(fname)
                
                # Start rec in ACQ and run task
                resp = socket_message(f"record_start::{subject_id_date}_{tsk_strt_time}_{t_obs_id}::{task}",
                                    "acquisition", wait_data=10)
                # print(resp)
                sleep(.5)

                events = tsk_fun.run(**this_task_kwargs)
                socket_message("record_stop", "acquisition", wait_data=15)
                print(f"Finished task:{task}")

                # Log tech_obs to database
                log_task["tech_obs_id"] = t_obs_id
                log_task['event_array'] = str(events).replace("'", '"') if events is not None else "event:datestamp"
                meta._fill_tech_obs_row(log_task_id, log_task, conn)     
                
                if streams.get('Eyelink') and any('Eyelink' in d for d in list(task_devs_kw[task])):
                    if 'calibration_task' not in task:
                        streams['Eyelink'].stop()
                
                sleep(2)
                # Check if pause requested, unpause or stop
                data = get_data_timeout(s1, .1)
                if data == "pause tasks":
                    pause_screen = utl.create_text_screen(win, text="Session Paused")
                    utl.present(win, pause_screen, waitKeys=False)
                    
                    connx2, _ = s1.accept()
                    data = connx2.recv(1024)
                    data = data.decode("utf-8")
                    
                    if data == "continue tasks":
                        continue                    
                    elif data == "stop tasks":
                        break
                    elif data == 'calibrate':
                        if not len(task_calib):
                            print("No calibration task")
                            continue
                        tasks.insert(0, task_calib[0])
                        calib_instructions = False
                        print("Calibration task added")
                    else:
                        print("While paused received another message")
                    
            finish_screen(win)
            presented = True

        elif data in ["close", "shutdown"]:
            streams = close_streams(streams)
            # print("Closing devices")

            if "shutdown" in data:
                if screen_running:
                    screen_feed.stop()
                    # print("Closing screen mirroring")
                    screen_running = False
                # print("Closing Stim server")
                break

        elif "time_test" in data:
            msg = f"ping_{time()}"
            connx.send(msg.encode("ascii"))

        else:
            print(data)

    s1.close()
    sys.stdout = sys.stdout.terminal
    win.close()


Main()
