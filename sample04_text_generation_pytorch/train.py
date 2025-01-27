import argparse
import torch
import numpy as np
from torch import nn, optim
from torch.utils.data import DataLoader
from model import Model
from dataset import Dataset


import torch_mlu
import torch_mlu.core.mlu_model as ct
global ct

device = torch.device('mlu' if torch.mlu.is_available() else 'cpu')


def train(dataset, model, args):
    model.train()

    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(args.max_epochs):
        state_h, state_c = model.init_state(args.sequence_length)
        state_h = state_h.to(device)
        state_c = state_c.to(device)

        for batch, (x, y) in enumerate(dataloader):
            x,y = x.to(device),y.to(device)

            optimizer.zero_grad()

            y_pred, (state_h, state_c) = model(x, (state_h, state_c))
            loss = criterion(y_pred.transpose(1, 2), y)

            state_h = state_h.detach()
            state_c = state_c.detach()

            loss.backward()
            optimizer.step()

            print({ 'epoch': epoch, 'batch': batch, 'loss': loss.item() })

def predict(dataset, model, text, next_words=100):
    words = text.split(' ')
    model.eval()

    state_h, state_c = model.init_state(len(words))

    state_h = state_h.to(device)
    state_c = state_c.to(device)


    for i in range(0, next_words):
        x = torch.tensor([[dataset.word_to_index[w] for w in words[i:]]]).to(device)
        y_pred, (state_h, state_c) = model(x, (state_h, state_c))
        last_word_logits = y_pred[0][-1]
        p = torch.nn.functional.softmax(last_word_logits, dim=0).detach().cpu().numpy()
        word_index = np.random.choice(len(last_word_logits), p=p)
        words.append(dataset.index_to_word[word_index])

    return words

parser = argparse.ArgumentParser()
parser.add_argument('--max-epochs', type=int, default=500)
parser.add_argument('--batch-size', type=int, default=256)
parser.add_argument('--sequence-length', type=int, default=4)
args = parser.parse_args()

dataset = Dataset(args)
model = Model(dataset)
model = model.to(device)

train(dataset, model, args)
print(predict(dataset, model, text='if you’ll take a tip'))
