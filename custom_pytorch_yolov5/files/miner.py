import cv2
import torch
from PIL import Image
from time import sleep
import os
import time
import datetime


import argparse
# parse arguments for different execution modes.
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--size', help='Minimum Pixel Size (how many pixels the crop detection needs to be)',
    default=100,
    type=int,
    required=False)
parser.add_argument('-c', '--confidence', help='Confidence threshold (%) on detections',
    default=0.7,
    type=float,
    required=False)
parser.add_argument('-f', '--frequency', help='How frequently to capture cropped detected objects',
    default=1,
    type=int,
    required=False)


args = parser.parse_args()

# Change the working directory to the folder this script is in.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

TOTAL_PEOPLE = 0
global SCALE_FACTOR_X
global SCALE_FACTOR_Y
SCALE_FACTOR_X = 0.0
SCALE_FACTOR_Y = 0.0

# Model
model = torch.hub.load('ultralytics/yolov5',
    'yolov5s',
    force_reload=True) # default yolov5.

# Get webcam interface via opencv-python
video = cv2.VideoCapture(1)
video.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
video.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

if not video.isOpened():
    print("Cannot open camera")
    exit()

# Infer via TorchHub and return the result
def infer(i):
    print('[{}] New Inference Iteration'.format(datetime.datetime.now()))

    # Get the current image from the webcam
    ret, img = video.read()
    # if frame is read correctly ret is True
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        return

    # Resize (while maintaining the aspect ratio) to improve speed and save bandwidth
    height, width, channels = img.shape
    global SCALE_FACTOR_X, SCALE_FACTOR_Y
    if SCALE_FACTOR_X == 0.0 and SCALE_FACTOR_Y == 0.0:
        SCALE_FACTOR_X = width / 640.0
        SCALE_FACTOR_Y = height / 640.0
    original_img = img
    img = cv2.resize(img, (640, 640))
    

    # Inference
    results = model([img], size=640) # batch of images

    # Results
    results.print()  
    

    results.xyxy[0]  # im1 predictions (tensor)
    process = results.pandas().xyxy[0]  # .sort_values('confidence')
    #      xmin    ymin    xmax   ymax  confidence  class    name
    # 0  749.50   43.50  1148.0  704.5    0.874023      0  person
    # 1  433.50  433.50   517.5  714.5    0.687988     27     tie


    print(process)
    count = len(process[process['name']=='person'])
    if (count) > 0:
        print('# People: {}'.format(count))
        global TOTAL_PEOPLE
        TOTAL_PEOPLE += count

    # Only execute this if we're on the frame that corresponds with the frequency from args.
    if (i % args.frequency) == 0:
        save_cropped_images(original_img, process) # save images before drawing over them.
    else:
        return None

    img = draw_over_image(img, process, count)

    return img

# maybe useful function in the future
def rescale_results(df):
    global SCALE_FACTOR_X, SCALE_FACTOR_Y
    df['scaledxmin'] = df.apply(lambda x: x['xmin'] * SCALE_FACTOR_X, inplace=True)
    df['scaledxmax'] = df.apply(lambda x: x['xmax'] * SCALE_FACTOR_X, inplace=True)
    df['scaledymin'] = df.apply(lambda x: x['ymin'] * SCALE_FACTOR_Y, inplace=True)
    df['scaledymax'] = df.apply(lambda x: x['ymax'] * SCALE_FACTOR_Y, inplace=True)

    return df


def save_cropped_images(img, df):

    for idx, row in df.iterrows():
        #print(row['xmin'], row['xmax'], row['ymin'], row['ymax'])
        xmin = int(row['xmin'] * SCALE_FACTOR_X)
        xmax = int(row['xmax'] * SCALE_FACTOR_X)
        ymin = int(row['ymin'] * SCALE_FACTOR_Y)
        ymax = int(row['ymax'] * SCALE_FACTOR_Y)
        print(xmin, xmax, ymin, ymax)

        try:
            assert (xmax - xmin) > args.size and (ymax - ymin) > args.size and row['confidence'] > args.confidence
        except AssertionError:
            continue # skip this detection as it doesn't have enough pixels as we asked for.

        # WATCH OUT! y goes first, then x.
        cropped_snip = img[ymin:ymax, xmin:xmax] # region of the screen I'm interested in 

        # DEBUG CROPPED IMAGES
        '''
        while True:
            try:
                cv2.imshow('Cropped', cropped_snip)
                key = cv2.waitKey(1)
                if key == ord('q'):
                    cv2.destroyAllWindows()
                    break
            except cv2.error:
                continue
        '''


        result = cv2.imwrite('./runs/detect/miner/{}_{}.jpg'.format(row['name'],
            time.time_ns() // 1000000),
            cropped_snip
        )



def draw_over_image(img, df, count):

    draw_color = (128, 128, 128) # grey
    for idx, row in df.iterrows():
        if row['name'] == 'person':
            draw_color = (0, 255, 0) # green
        else:
            draw_color = (128, 128, 128)
        
        # FONT_HERSHEY_SIMPLEX
        img = cv2.rectangle(img=img, pt1=(int(row['xmin']), int(row['ymin'])),
            pt2=(int(row['xmax']), int(row['ymax'])),
            color=draw_color,
            thickness=1
        )

        cv2.putText(img, row['name'], (int(row['xmin'])-10, int(row['ymin'])-10),
            cv2.FONT_HERSHEY_PLAIN, 1,
            draw_color
        )

        cv2.putText(img, row['name'], (int(row['xmin'])-10, int(row['ymin'])-10),
            cv2.FONT_HERSHEY_PLAIN, 1,
            draw_color
        )

        global TOTAL_PEOPLE
        cv2.putText(img, 'People: {}{}Total Detected Objects: {}'.format(count, '\n', TOTAL_PEOPLE), (25, 25),
            cv2.FONT_HERSHEY_PLAIN, 1.2,
            draw_color
        )

    return img

# Main loop; infers sequentially until you press "q"
i = 1 # this will be our iterator for getting 1 every N frames (see args.frequency)
while True:


    # Capture start time to calculate fps
    start = time.time()

    # Get a prediction
    image, results = infer(i)

    if not image:
        continue # skip iteration

    cv2.imshow('Predicted', image)
    key = cv2.waitKey(1)
    if key == ord('q'):
        break

    # Print frames per second
    print('{} fps'.format(1/(time.time()-start)))

    i+= 1


# Release resources when finished
cv2.destroyAllWindows()
video.release()