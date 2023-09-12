import metadator
import logging

task_id = 1
conn = metadator.get_conn("mock_neurobooth_1")
task_stim_id, task_dev, task_sens, instr_kwargs = metadator._get_task_param(task_id, conn)