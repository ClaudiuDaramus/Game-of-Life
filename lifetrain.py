import cv2
import numpy as np
import sys
import torch
import torch.nn.functional as F
from PIL import Image

import pickle

BOARD_HEIGHT = 100
BOARD_WIDTH = 100

examples = torch.load('train.data.batch')
device = torch.device("cpu")
print(device)
trainloader = torch.utils.data.DataLoader(examples, batch_size=8,
                                          shuffle=True, num_workers=1)

cv2.namedWindow("game", cv2.WINDOW_NORMAL)


class GoL(torch.nn.Module):
    def __init__(self):
        super(GoL, self).__init__()
        self.conv1 = torch.nn.Conv2d(1, 1, (3, 3), padding=1)
        self.fc1 = torch.nn.Linear(BOARD_HEIGHT * BOARD_WIDTH, BOARD_HEIGHT * BOARD_WIDTH)

    def forward(self, x):
        x = self.conv1(x)
        x = self.fc1(x.view(-1, BOARD_HEIGHT * BOARD_WIDTH))
        x = F.selu(x)
        return x.view(-1, 1, BOARD_HEIGHT, BOARD_WIDTH)

if __name__ == '__main__':
    gol = GoL().to(device)

    # open a file, where you ant to store the data
    # file = open('important', 'wb')

    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(gol.parameters(), lr=0.001)
    for epoch in range(16):

        running_loss = 0.0
        for i, data in enumerate(trainloader):
            last_frame, target_ = data
            target_ = target_.view(-1, 1, BOARD_HEIGHT, BOARD_WIDTH).to(torch.float32).to(device)
            last_frame = last_frame.view(-1, 1, BOARD_HEIGHT, BOARD_WIDTH).to(torch.float32).to(device)
            input_ = last_frame

            optimizer.zero_grad()

            output_ = gol(input_)
            loss = criterion(output_, target_) * 56  # loss on non-aliver is penalized more
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            if i % 20 == 0:
                print('[%d, %5d] loss: %.3f' % (epoch + 1, i + 1, running_loss / 20))
                running_loss = 0.0
                newboard_array = np.int8(output_[0, ...].cpu().clone().view(BOARD_HEIGHT, BOARD_WIDTH).detach()) * 255
                img = Image.fromarray(newboard_array).convert('RGB')
                img = np.array(img)
                cv2.imshow("game", img)
                q = cv2.waitKey(100)
            last_frame = data

            # dump information to that file
            # pickle.dump(data, file)

    distrib = torch.distributions.Bernoulli(0.5)
    board = distrib.sample((BOARD_HEIGHT, BOARD_WIDTH)).view(1, 1, BOARD_HEIGHT, BOARD_WIDTH)
    board = board.to(torch.float32).to(device)

    # close the file
    # file.close()

    while True:
        board_array = np.int8(board.clone().cpu().view(BOARD_HEIGHT, BOARD_WIDTH).detach()) * 255
        img = Image.fromarray(board_array).convert('RGB')
        img = np.array(img)
        cv2.imshow("game", img)

        newboard = gol(board)

        q = cv2.waitKey(200)
        if q == 113:  # 'q'
            cv2.destroyAllWindows()
            break
        if q == 114:  # 'r'
            distrib = torch.distributions.Bernoulli(0.5)
            board = distrib.sample((BOARD_HEIGHT, BOARD_WIDTH)).view(1, 1, BOARD_HEIGHT, BOARD_WIDTH)
            board = board.to(torch.float32).to(device)
            newboard = board
        board = newboard
