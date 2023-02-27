import torch
from PIL import ImageGrab
import argparse
import time
import cv2
import numpy as np

# parse arguments for different execution modes.
parser = argparse.ArgumentParser()
parser.add_argument('-m', '--model', help='Model path',
    type=str,
    required=True)
parser.add_argument('-d', '--detect', help='Detection mode (league / screen)',
    choices=['league', 'screenshot'],
    default='screenshot',
    type=str,
    required=False
)

args = parser.parse_args()


# Model
model = torch.hub.load('ultralytics/yolov5',
    'custom',
    path=args.model,
    force_reload=False)


def draw_over_image(img, df):

    draw_color = (255, 255, 255)
    yellow = (128, 128, 0)
    green = (0, 255, 0)
    red = (255, 0, 0)
    for idx, row in df.iterrows():
        # FONT_HERSHEY_SIMPLEX
        if row['name'] == 'mask':
            draw_color = green
        elif row['name'] == 'incorrect':
            draw_color = yellow
        else:
            draw_color = red
        img = cv2.rectangle(img=img, pt1=(int(row['xmin']), int(row['ymin'])),
            pt2=(int(row['xmax']), int(row['ymax'])),
            color=draw_color,
            thickness=5
        )

        cv2.putText(img, row['name'], (int(row['xmin'])-10, int(row['ymin'])-10), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=draw_color, thickness=2
        )

        cv2.putText(img, row['name'], (int(row['xmin'])-10, int(row['ymin'])-10), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=draw_color, thickness=2
        )

    return img

# Main loop; infers sequentially until you press "q"
while True:

    # Image
    if args.detect == 'league':   
        im = ImageGrab.grab(bbox=(2140+100, 1030+100, 2560-100, 1440-100)) # bbox=(2140, 1030, 2560, 1440))
    else:
        im = ImageGrab.grab() # take a screenshot

    img = np.array(im)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    #img = cv2.resize(img, (1280, 1024))
    
    # Inference
    results = model(img)
    # Capture start time to calculate fps
    start = time.time()

    print(results.pandas().xyxy[0])

    #results.show()



    cv2.imshow('Image', draw_over_image(img, results.pandas().xyxy[0]))
    key = cv2.waitKey(30)
    if key == ord('q'):
        cv2.destroyAllWindows()
        break

    # Print frames per second
    print('{} fps'.format(1/(time.time()-start)))