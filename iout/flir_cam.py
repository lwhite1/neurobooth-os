# -*- coding: utf-8 -*-
"""
Created on Wed May 12 16:13:50 2021

@author: CTR
"""

import PySpin
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import cv2
import threading
import uuid
from pylsl import StreamInfo, StreamOutlet




class VidRec_Flir():        
    def __init__(self, fourcc=cv2.VideoWriter_fourcc(*'MJPG'),
                 sizex=round(1936/2), sizey=round(1216/2), fps=160, 
                 camSN="20522874", exposure=4500, gain=20, gamma=.6):
        
        self.open = False
        self.serial_num = camSN 
        self.fourcc = fourcc
        self.fps = fps 
        self.serial_num = camSN
        self.exposure = exposure
        self.gain = gain
        self.gamma = gamma
        
        self.get_cam()
        self.setup_cam()
        
        
        
    def get_cam(self):
        self.system = PySpin.System.GetInstance()
        cam_list = self.system.GetCameras()
        self.cam = cam_list.GetBySerial(self.serial_num)        
        
        
    def setup_cam(self):        
        self.cam.Init()
        self.open = True
        self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)        
        self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                
        self.cam.ExposureTime.SetValue(self.exposure)
        self.cam.Gamma.SetValue(self.gamma)
        self.cam.Gain.SetValue(self.gain)
        self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Once)
        # cam.BalanceWhiteAuto.SetValue(0)


    def createOutlet(self, filename):
        streamName = 'FlirFrameIndex'
        self.oulet_id = str(uuid.uuid4())
        info = StreamInfo(name=streamName, type='videostream', channel_format='int32', channel_count=2,
                          source_id=self.oulet_id)
        
        info.desc().append_child_value("videoFile", filename)
 
        info.desc().append_child_value("size_rgb", str(self.frameSize)) 
        info.desc().append_child_value("serial_number", self.serial_num) 
        info.desc().append_child_value("fps_rgb", str(self.fps))
        # info.desc().append_child_value("device_model_id", self.cam.get_device_name().decode())
        print(f"-OUTLETID-:{streamName}:{self.oulet_id}")
        return StreamOutlet(info)


    def start(self, name="temp_video"):        
        self.prepare(name)
        self.video_thread = threading.Thread(target=self.record)
        self.video_thread.start()  


    def prepare(self, name="temp_video"):
        self.cam.BeginAcquisition()
        im = self.cam.GetNextImage(1000)
        self.frameSize = (im.GetWidth(), im.GetHeight())
        self.video_filename ="{}_ximea_{}.avi".format(name, time.time())    
        self.video_out = cv2.VideoWriter(self.video_filename, self.fourcc,
                                         self.fps, self.frameSize)
        self.outlet = self.createOutlet(self.video_filename)
        self.streaming = True

    def record(self):   
        self.recording = True
        self.frame_counter = 0

        print(f"FLIR recording {self.video_filename}")
        t0 = time.time()
        self.image_queue = []
        self.stamp = []
        while self.recording:   
            im = self.cam.GetNextImage(1000)
            tsmp = im.GetTimeStamp()
            # im_conv = im.Convert(PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)
            # im_conv_d = im_conv.GetData()
            
            self.image_queue.append(im.GetData())
            #   stamp.append(time.time_ns())
            self.stamp.append(tsmp)
            
            #  Release image
            #
            #  *** NOTES ***
            #  Images retrieved directly from the camera (i.e. non-converted
            #  images) need to be released in order to keep from filling the
            #  buffer.
            im.Release()


            try:
                self.outlet.push_sample([self.frame_counter, tsmp])
            except:  # "OSError" from C++
                print(f"Reopening FLIR {self.device_index} stream already closed")
                self.outlet = self.createOutlet(self.video_filename)
                self.outlet.push_sample([self.frame_counter])

            # self.video_out.write(im_conv_d)
            self.frame_counter += 1

        print(f"FLIR recording ended with {self.frame_counter} frames in {time.time()-t0}")
        self.cam.EndAcquisition() 
        self.recording = False  
        self.video_out.release()    

    def stop(self):
        if self.open and self.recording:
            self.recording = False 
            self.video_thread.join()
                     
        self.streaming = False
       
    def close(self):
        self.stop()        
        self.cam.DeInit()
        self.open = False
        
if __name__ == "__main__":

    ximi = VidRec_Flir()
    ximi.start()
    time.sleep(10)
    ximi.close()
    ximi.frameSize