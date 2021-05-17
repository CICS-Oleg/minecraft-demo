import logging
import random
import shutil
import os
import pickle
import torch.nn.functional as F
import numpy
from collections import namedtuple
import torch
import torch.nn as nn
from torch.distributions.beta import Beta
from torch.distributions.categorical import Categorical


def init_weights_xavier(m):
    if type(m) == nn.Linear:
        torch.nn.init.xavier_uniform(m.weight)
        m.bias.data.fill_(0.01)


class Action:
    def to_string(self, value):
        return self.name + ' ' + str(value.item())


class ContiniousAction(Action):
    def __init__(self, name, _min, _max):
        self.name = name
        self.min = _min
        self.max = _max

    def scale(self, x):
        return x * (self.max - self.min) + self.min

    def inv_scale(self, x):
        return (x - self.min) / (self.max - self.min)


class BinaryAction(Action):
    def __init__(self, name):
        self.name = name

    def scale(self, x):
        return x

    def inv_scale(self, x):
        return x


class CategoricalAction(Action):
    def __init__(self, names):
        self.names = names

    def to_string(self, value):
        return self.names[value]

    def inv_scale(self, x):
        return x

    def __len__(self):
        return len(self.names)


class ContiniousActionAgent(nn.Module):
    def __init__(self, actions, grid_len, grid_w,
                 target_enc_len, pos_enc_len):
        super().__init__()
        num = 256
        self.actions = actions
        self.grid_enc = nn.Sequential(
            nn.Linear(grid_w * grid_len, num),
            nn.LeakyReLU(),
            nn.Linear(num, 20),
            nn.LeakyReLU())

        self.trunk = nn.Sequential(
            nn.Linear(20 + target_enc_len + pos_enc_len , num),
            nn.LeakyReLU(inplace=False),

            nn.Linear(num, num),
            nn.LeakyReLU(inplace=False),

            nn.Linear(num, num),
            nn.LeakyReLU(inplace=False)
        )

        self.cont_actions = [x for x in actions if isinstance(x, ContiniousAction)]
        self.binary_actions = [x for x in actions if isinstance(x, BinaryAction)]
        self.categorical_actions = [x for x in actions if isinstance(x, CategoricalAction)]
        self.action_output = nn.Sequential(
            nn.Linear(num, num),
            nn.LeakyReLU(inplace=False),

            nn.Linear(num, num),
            nn.LeakyReLU(inplace=False),

            nn.Linear(num, num),
            nn.LeakyReLU(inplace=False),

            # continious actions are modeled by Beta distribution which requires two parameters
            # binary actions are modeled by categorical distribution, which requires one parameter
            nn.Linear(num, len(self.cont_actions) * 2 + len(self.binary_actions) + sum(len(x) for x in self.categorical_actions) )
            )
        self.prev_dist = []
        self.prev_actions = []
        self.apply(init_weights_xavier)

    def forward(self, data):
        grid_vec = data['grid_vec']
        target = data['target']
        pos = target['pos']
        prev_pos = target['previous_pos']
        params = next(self.parameters())
        # process grid
        grid_enc = self.grid_enc(grid_vec.to(params).flatten())
        # concat grid with other inputs

        self.prev_actions = []
        self.prev_dist = []
        enc = torch.cat([grid_enc.squeeze(), target, pos], dim=0)
        dense = self.trunk(enc)

        params = torch.abs(self.action_output(dense))
        len_cont = len(self.cont_actions) * 2
        len_binary = len(self.binary_actions)
        len_cat = len(self.categorical_actions)
        beta_params = params[:len_cont]
        binary_params = torch.sigmoid(params[len_cont: len_cont + len_binary])
        cat_params = torch.nn.functional.softmax(params[len_cont + len_binary:])

        actions = []
        beta_params = beta_params.reshape((len(beta_params) // 2, 2))
        # actions
        for a, param in zip(self.cont_actions, beta_params):
            dist = Beta(*param)
            self.prev_dist.append(dist)
            act = dist.sample()
            self.prev_actions.append(act)
            actions.append(a.to_string(a.scale(act)))
        for a, param in zip(self.binary_actions, binary_params):
            dist = Categorical(torch.as_tensor([param, 1 - param]))
            self.prev_dist.append(dist)
            act = dist.sample()
            self.prev_actions.append(act)
            actions.append(a.to_string(act))
        if self.categorical_actions:
            assert(len(self.categorical_actions) == 1)
            a = self.categorical_actions[0]
            dist = Categorical(cat_params)
            self.prev_dist.append(dist)
            act = dist.sample()
            self.prev_actions.append(act)
            actions.append(a.to_string(act))
        return actions

    def compute_loss(self, reward, eps=0.00000001):
        loss = 0
        for a, action, dist in zip(self.actions, self.prev_actions, self.prev_dist):
            loss = - dist.log_prob(action + eps) * reward + loss
            if torch.isinf(loss):
                import pdb;pdb.set_trace()
        logging.debug('loss ', loss)
        return loss


class DQN:
    def __init__(self, gamma, batch_size, target_update, *args, capacity=500, **kwargs):
        self.policy_net = QNetwork(*args, **kwargs)
        self.target_net = QNetwork(*args, **kwargs)
        self.target_update = target_update
        self.iteration = 0
        self.prev_state = None
        self.prev_action = None
        self.memory = ReplayMemory(capacity)
        self.memory_path = 'memory.pkl'
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'rb') as f:
                logging.debug('loading %s', self.memory_path)
                self.memory = pickle.load(f)
                self.memory.capacity = capacity
                self.memory.memory = [x for x in self.memory.memory if x is not None]
                self.memory.position = random.randint(0, len(self.memory))
        self.gamma = gamma
        self.batch_size = batch_size

    def parameters(self):
        return self.policy_net.parameters()

    def train(self):
        return self.policy_net.train()

    def clear_state(self):
        self.prev_state = None
        self.prev_action = None

    def push_final(self, reward):
        if self.prev_state == None:
            return
        self.memory.push(self.prev_state,
                         self.prev_action,
                         None, torch.as_tensor(reward))
        self.prev_state = None
        self.prev_action = None

    def __call__(self, state, reward=0, **kwargs):
        # use policy network
        with torch.no_grad():
            action = self.policy_net.sample(state, **kwargs)
        if self.prev_state is not None:
            self.memory.push(self.prev_state,
                         self.prev_action, state, torch.as_tensor(reward))
        self.prev_state = state
        self.prev_action = action
        return [self.policy_net.actions[0].to_string(action)]

    def compute_loss(self):
        if len(self.memory) < 5:
            return None
        transitions = self.memory.sample(min(self.batch_size, len(self.memory)))
        batch = Transition(*zip(*transitions))
        state_batch = dict()
        for k in batch.state[0].keys():
            state_batch[k] = torch.stack([data[k] for data in batch.state])

        action_batch = torch.cat(batch.action)
        reward_batch = torch.stack(batch.reward)
        next_states = batch.next_state

        # Compute Q(s_t, a) - the model computes Q(s_t), then we select the
        # columns of actions taken. These are the actions which would've been taken
        # for each batch state according to policy_net
        state_action_values = self.policy_net(state_batch)
        Q_values = state_action_values[numpy.arange(len(state_action_values)), action_batch]

        # Compute a mask of non-final states and concatenate the batch elements
        # (a final state would've been the one after which simulation ended)
        non_final_mask = torch.tensor(tuple(map(lambda s: s is not None,
                                              batch.next_state)), dtype=torch.bool)
        non_final_next_states = [s for s in batch.next_state
                                                if s is not None]

        non_final_state = dict()
        for k in non_final_next_states[0].keys():
            non_final_state[k] = torch.stack([data[k] for data in non_final_next_states])


        next_Q_values = torch.zeros(len(non_final_mask))

        # argmax a' Q(s', a')
        next_Q_values[non_final_mask] = self.target_net(non_final_state).max(1)[0].detach()

        # E[r + gamma argmax a' Q(s', a', theta)]
        expected_Q_values = (next_Q_values * self.gamma) + reward_batch

        # Compute Huber loss
        #loss = F.smooth_l1_loss(Q_values, expected_Q_values, beta=101)
        loss = F.mse_loss(Q_values, expected_Q_values)
        self.iteration += 1
            # Update the target network, copying all weights and biases in DQN
        if self.iteration % self.target_update == 0:
            # save memory
            tmp_path = self.memory_path + 'tmp'
            with open(tmp_path, 'wb') as f:
                pickle.dump(self.memory, f)
            shutil.move(tmp_path, self.memory_path)
            logging.debug('update target network')
            with torch.no_grad():
                for pol_param, target_param in zip(self.policy_net.parameters(),
                                                   self.target_net.parameters()):
                    mean = 0.4 * pol_param.detach().numpy() + 0.6 * target_param.detach().numpy()
                    target_param[:] = torch.as_tensor(mean)
                    # pol_param[:] = torch.as_tensor(mean)
        return loss

    def state_dict(self):
        return self.target_net.state_dict()

    def load_state_dict(self, state_dict, strict=True):
        self.policy_net.load_state_dict(state_dict, strict)
        return self.target_net.load_state_dict(state_dict, strict)


class QNetwork(ContiniousActionAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_actions = sum(len(x) for x in self.categorical_actions)

    def forward(self, data):
        """
        Estimate and return Q-value for each action
        """
        params = next(self.parameters())
        # process grid
        grid_enc = self.grid_enc(data['grid_vec'].to(params).flatten(-2))


        target = data['target']
        pos = data['pos']

        # concat grid with other inputs
        if len(grid_enc.shape) == 1:
            grid_enc = grid_enc.unsqueeze(0)
            target = target.unsqueeze(0)
            pos = pos.unsqueeze(0)
        enc = torch.cat([grid_enc,
                         target,
                         pos], dim=1)

        x = self.trunk(enc)
        q_values = self.action_output(x)
        return q_values

    def sample(self, *args, epsilon=0.05):
        num = random.random()
        with torch.no_grad():
             q_values = self(*args)

        if num > epsilon:
            act = torch.argmax(q_values).unsqueeze(0)
            logging.debug('argmax action')
        else:
            device = next(self.parameters()).device
            if q_values.min() < 0:
                q_values -= q_values.min()
            # make action different from argmax
            q_values[0, q_values.argmax()] /= 2
            act = Categorical(q_values).sample()
            # act = torch.tensor([random.randrange(self.n_actions)], device=device)
            logging.debug('random action')
        return act


Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward'))


class ReplayMemory:

    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.position = 0

    def push(self, *args):
        """Saves a transition."""
        transition = Transition(*args)
        if len(self.memory) < self.capacity:
            self.memory.append(transition)
        else:
            self.memory[self.position] =  transition
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)
