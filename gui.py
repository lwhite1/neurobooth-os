# -*- coding: utf-8 -*-
"""
Created on Fri Apr  2 08:01:51 2021

@author: neurobooth
"""

import PySimpleGUI as sg
import main_control_rec as ctr_rec
# Turn off padding in order to get a really tight looking layout.
def callback_RTD(values):    
    ctr_rec.prepare_feedback() # rint resp
    
def get_session_info(values):
     session_info = values        
     tasks = get_tasks(values)
     return session_info, tasks
    
def get_tasks(values):
    non_task = ['subj_id', 'rc_id']
    tasks= []
    for key, val in values.items():
        if key not in non_task and val == True:
            tasks.append(val)
    return tasks            
    

def lay_butt(name, key):
    if key is None:
        key = name
    return sg.Button(name, button_color=('white', 'black'), key=key)

space = sg.Text(' ' * 10)

sg.theme('Dark Grey 9')
sg.set_options(element_padding=(0, 0))
layout = [[sg.Text('Subject ID:', pad=((0, 0), 0), justification='left'), sg.Input(key='subj_id', size=(44, 1), background_color='white', text_color='black')],
          [space],
          [sg.Text('RC ID:', pad=((0, 0), 0), justification='left'), sg.Input(key='rc_id', size=(44, 1), background_color='white', text_color='black')],
          [space],
          [sg.Text('RC Notes:', pad=((0, 0), 0), justification='left'),  sg.Multiline(key='notes', default_text='', size=(44, 25))],
          [space],
          [space, sg.Checkbox('Symbol Digit Matching Task', key='fakest_task', size=(44, 1))],
          [space, sg.Checkbox('Mouse Task', key='extra_fakest_task', size=(44, 1))],
          [space],          
          [space, sg.ReadFormButton('Save', button_color=('white', 'black'))],         
          [space],
          [space],
          [sg.Text('Console Output:', pad=((0, 0), 0), justification='left'), sg.Multiline(key='console', default_text='', size=(44, 15))],
          [space],
          [space],
          [space, lay_butt('Test Comm', 'Test_network'),space,  
            lay_butt('Prepare Devices', 'Devices') ],
          [space],
          [space, sg.ReadFormButton('Start', button_color=('white', 'black')), space, lay_butt('Stop')],
          [space],
          ]
window = sg.Window("Neurobooth",
                   layout,
                   default_element_size=(12, 1),
                   text_justification='r',
                   auto_size_text=False,
                   auto_size_buttons=False,
                   no_titlebar=False,
                   grab_anywhere=False,
                   default_button_element_size=(12, 1))

session_saved = False

while True:             # Event Loop
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    elif event == 'RTD':
        ctr_rec.prepare_feedback()
        
    elif event == 'Devices':
        ctr_rec.prepare_devices()
        ctr_rec.initiate_labRec()
        
    elif event == 'Save':
        session_info = values        
        tasks = get_tasks(values)
        session_saved = True
        
    elif event == 'Test_network':
        ctr_rec.test_lan_delay(50)
        
    elif event == 'Start':
        if not session_saved:
            session_info, tasks =  get_session_info(values)
          
        ctr_rec.task_loop(tasks, session_info['subj_id']) 
        
        # session
    elif event == 'Stop':
        ctr_rec.close_all()
        session_saved = False
        
window.close()