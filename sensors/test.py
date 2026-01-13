from time import sleep
import gpiozero
import motor_helper as mh

try:
    
    # # startup for script
    # mh.stop() 
    # sleep(5)
    
    # print("testing forward")
    # mh.forward(0.5)
    # sleep(2)

    # print("testing backward")
    # mh.backward(0.5)
    # sleep(2)
    
    # print("testing stop")
    # mh.stop()
    # sleep(2)

    print("testing turn left")
    mh.turn_left(1.0)
    sleep(2)
    mh.stop()
    sleep(2)
    
    print("testing turn right")
    mh.turn_right(1.0)
    sleep(2)

except KeyboardInterrupt:
    mh.stop()






    