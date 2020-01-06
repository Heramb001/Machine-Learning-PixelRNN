import logging
logging.basicConfig(format="[%(asctime)s] %(message)s", datefmt="%m-%d %H:%M:%S")

import numpy as np
import tensorflow as tf
from tensorflow.python.ops import rnn_cell

# tensorflow/contrib/rnn/python/ops/core_rnn_cell.py
from tensorflow.contrib.rnn.python.ops import core_rnn_cell
from tensorflow.examples.tutorials.mnist import input_data
from tensorflow.contrib.layers import variance_scaling_initializer

WEIGHT_INITIALIZER = tf.contrib.layers.xavier_initializer()
#WEIGHT_INITIALIZER = tf.uniform_unit_scaling_initializer()

logger = logging.getLogger(__name__)

he_uniform = variance_scaling_initializer(factor=2.0, mode="FAN_IN", uniform=False)
data_format = "NCHW"

def get_shape(layer):
  return layer.get_shape().as_list()

#def get_shape(layer):
#  if data_format == "NHWC":
#    batch, height, width, channel = layer.get_shape().as_list()
#  elif data_format == "NCHW":
#    batch, channel, height, width = layer.get_shape().as_list()
#  else:
#    raise ValueError("Unknown data_format: %s" % data_format)
#  return batch, height, width, channel
"""
 inputs.shape: (batch_size, height, width, dim)
 outputs.shape: (batch_size, height, width+height-1, dim)
"""
def skew(inputs, scope="skew"):
    with tf.variable_scope(scope):
        batch_size, height, width, dim = inputs.get_shape().as_list()
        print(dim)
        print(height)
        rows = tf.split(inputs, height, 1)
        new_width = width + height - 1
        new_rows = []
        for idx, row in enumerate(rows):
            transposed_row = tf.transpose(tf.squeeze(row, [1]), [0, 2, 1]) # [batch_size, dim, width]
            squeezed_row = tf.reshape(transposed_row, [-1, width]) # [batch_size*dim, width]
            padded_row = tf.pad(squeezed_row, ((0, 0), (idx, height - 1 - idx))) # [batch_size*dim, width+height-1]
            unsqueezed_row = tf.reshape(padded_row, [-1, dim, new_width]) # [batch, dim, width+height-1]
            untransposed_row = tf.transpose(unsqueezed_row, [0, 2, 1]) # [batch, width+height-1, dim]
            new_rows.append(untransposed_row)
        outputs = tf.stack(new_rows, axis=1, name='output')
        return outputs

"""
  inputs.shape: (batch_size, height, skewed_width, dim)
  outputs.shape: (batch_size, height, width, dim)
"""

def unskew(inputs, width=None, scope="unskew"):
    with tf.name_scope(scope):
        batch_size, height, skewed_width, dim = inputs.get_shape().as_list()
        width = width if width else height
        rows = tf.split(inputs, height, 1)
        new_rows = []
        for idx, row in enumerate(rows):
            new_rows.append(tf.slice(row, [0, 0, idx, 0], [-1, -1, width, -1]))
        outputs = tf.concat(new_rows, axis=1, name='output')
        return outputs

def conv2d(
    inputs,
    num_outputs,
    kernel_shape, # [kernel_height, kernel_width]
    mask_type, # None, "A" or "B",
    strides=[1, 1], # [column_wise_stride, row_wise_stride]
    padding="SAME",
    activation_fn=None,
    weights_initializer=WEIGHT_INITIALIZER,
    weights_regularizer=None,
    biases_initializer=tf.zeros_initializer(),
    biases_regularizer=None,
    scope="conv2d"):
  with tf.compat.v1.variable_scope(scope):
    mask_type = mask_type.lower()
    batch_size, height, width, channel = inputs.get_shape().as_list()

    kernel_h, kernel_w = kernel_shape
    stride_h, stride_w = strides

    assert kernel_h % 2 == 1 and kernel_w % 2 == 1, \
      "kernel height and width should be odd number"

    center_h = kernel_h // 2
    center_w = kernel_w // 2

    weights_shape = [kernel_h, kernel_w, channel, num_outputs]
    weights = tf.compat.v1.get_variable("weights", weights_shape,
      tf.float32, weights_initializer, weights_regularizer)

    if mask_type is not None:
      mask = np.ones(
        (kernel_h, kernel_w, channel, num_outputs), dtype=np.float32)

      mask[center_h, center_w+1: ,: ,:] = 0.
      mask[center_h+1:, :, :, :] = 0.

      if mask_type == 'a':
        mask[center_h,center_w,:,:] = 0.

      weights *= tf.constant(mask, dtype=tf.float32)
      tf.compat.v1.add_to_collection('conv2d_weights_%s' % mask_type, weights)

    outputs = tf.nn.conv2d(inputs,
        weights, [1, stride_h, stride_w, 1], padding=padding, name='outputs')
    tf.compat.v1.add_to_collection('conv2d_outputs', outputs)

    if biases_initializer != None:
      biases = tf.compat.v1.get_variable("biases", [num_outputs,],
          tf.float32, biases_initializer, biases_regularizer)
      outputs = tf.nn.bias_add(outputs, biases, name='outputs_plus_b')

    if activation_fn:
      outputs = activation_fn(outputs, name='outputs_with_fn')

    logger.debug('[conv2d_%s] %s : %s %s -> %s %s' \
        % (mask_type, scope, inputs.name, inputs.get_shape(), outputs.name, outputs.get_shape()))

    return outputs

def conv1d(
    inputs,
    num_outputs,
    kernel_size,
    strides=[1, 1], # [column_wise_stride, row_wise_stride]
    padding="SAME",
    activation_fn=None,
    weights_initializer=WEIGHT_INITIALIZER,
    weights_regularizer=None,
    biases_initializer=tf.zeros_initializer(),
    biases_regularizer=None,
    scope="conv1d"):
  with tf.compat.v1.variable_scope(scope):
    batch_size, height, _, channel = inputs.get_shape().as_list() # [batch, height, 1, channel]

    kernel_h, kernel_w = kernel_size, 1
    stride_h, stride_w = strides

    weights_shape = [kernel_h, kernel_w, channel, num_outputs]
    weights = tf.compat.v1.get_variable("weights", weights_shape,
      tf.float32, weights_initializer, weights_regularizer)
    tf.compat.v1.add_to_collection('conv1d_weights', weights)

    outputs = tf.nn.conv2d(inputs,
        weights, [1, stride_h, stride_w, 1], padding=padding, name='outputs')
    tf.compat.v1.add_to_collection('conv1d_outputs', weights)

    if biases_initializer != None:
      biases = tf.compat.v1.get_variable("biases", [num_outputs,],
          tf.float32, biases_initializer, biases_regularizer)
      outputs = tf.nn.bias_add(outputs, biases, name='outputs_plus_b')

    if activation_fn:
      outputs = activation_fn(outputs, name='outputs_with_fn')

    logger.debug('[conv1d] %s : %s %s -> %s %s' \
        % (scope, inputs.name, inputs.get_shape(), outputs.name, outputs.get_shape()))

    return outputs

class DiagonalLSTMCell(rnn_cell.RNNCell):
    def __init__(self, hidden_dim, height, input_dim):
        super(DiagonalLSTMCell, self).__init__(_reuse=True)
        self._height = height
        self._input_dim = input_dim
        self._hidden_dim = hidden_dim
        self._num_units = self._hidden_dim * self._height
        self._state_size = self._num_units * 2
        self._output_size = self._num_units

    @property
    def state_size(self):
        return self._state_size

    @property
    def output_size(self):
        return self._output_size

    def __call__(self, i_to_s, state, scope="DiagonalBiLSTMCell"):
        c_prev = tf.slice(state, [0, 0], [-1, self._num_units])
        h_prev = tf.slice(state, [0, self._num_units], [-1, self._num_units]) # [batch_size, height*hidden_dim]
        # i_to_s : [batch, 4 * height * hidden_dim]
        with tf.variable_scope(scope):
            # input-to-state (K_ss * h_{i-1}) : 2x1 convolution. generate 4h x n x n tensor.
            conv1d_inputs = tf.reshape(h_prev,
                [-1, self._height, 1, self._hidden_dim], name='conv1d_inputs') # [batch, height, 1, hidden_dim]
            conv_s_to_s = conv1dRNN(conv1d_inputs,
                self._hidden_dim, 4 * self._hidden_dim, 2, False, scope='s_to_s') # [batch, height, 1, hidden_dim * 4]
            print(scope+'_conv_s_to_s:', conv_s_to_s.shape)
            print(scope+'_i_to_s:', i_to_s.shape)
            s_to_s = tf.reshape(conv_s_to_s,
                [-1, self._height * self._hidden_dim * 4]) # [batch, height * hidden_dim * 4]
            print(scope+'_s_to_s:', s_to_s.shape)
            gates = i_to_s + s_to_s
            o, f, i, g = tf.split(gates, 4, 1)
            o = tf.sigmoid(o)
            f = tf.sigmoid(f)
            i = tf.sigmoid(i)
            g = tf.tanh(g)
            print(scope+'_o:', o.shape)
            print(scope+'_f:', f.shape)
            print(scope+'_i:', i.shape)
            print(scope+'_g:', g.shape)
            c = f*c_prev + i*g
            h = o * tf.tanh(c)
        new_state = tf.concat([c, h], 1)
        return h, new_state


def diagonal_lstm(inputs, input_dim, hidden_dim, scope='diagonal_lstm'):
    with tf.variable_scope(scope):
        skewed_inputs = skew(inputs, scope='skewed_i')
        print(scope + '_skewed_inputs:', skewed_inputs.shape)
        # input-to-state (K_is * x_i) : 1x1 convolution. generate 4h x n x n tensor.
        input_to_state = conv2dRNN(skewed_inputs, input_dim, hidden_dim * 4, 1, 'b', scope='i_to_s')
        _, height, skewed_width, dim = input_to_state.get_shape().as_list()

        print(scope + ' input_to_state:', input_to_state.shape)
        rnn_inputs = tf.transpose(
            input_to_state, [0, 2, 1, 3]) # [batch_size, width, height, hidden_dim * 4]
        print(scope + ' rnn_inputs:', rnn_inputs.get_shape().as_list())
        rnn_inputs = tf.reshape(rnn_inputs, [-1, skewed_width, height * dim])
        print(scope + ' rnn_inputs1:', rnn_inputs.shape)

        cell = DiagonalLSTMCell(hidden_dim, height, input_dim)
        outputs, states = tf.nn.dynamic_rnn(cell,
            inputs=rnn_inputs, dtype=tf.float32) # [batch, width, height * hidden_dim]
        print('diagonal_lstm_dynamic_rnn:', outputs.shape)
        outputs = tf.reshape(outputs, [-1, skewed_width, height, hidden_dim])
        
        outputs = tf.transpose(outputs, [0, 2, 1, 3])
        print('diagonal_lstm_outputs0:', outputs.shape)
        outputs = unskew(outputs)
        print('diagonal_lstm_outputs3:', outputs.shape)
        return outputs

def diagonal_bilstm(inputs, input_dim, hidden_dim, scope='diagonal_bilstm'):
    with tf.variable_scope(scope):
        def reverse(inputs):
            return tf.reverse(inputs, [2]) # [False, False, True, False])
    
        output_state_fw = diagonal_lstm(inputs, input_dim, hidden_dim, scope='output_state_fw')
        output_state_bw = reverse(diagonal_lstm(reverse(inputs), input_dim, hidden_dim, scope='output_state_bw'))
        batch_size, height, width, dim = output_state_bw.get_shape().as_list()
        output_state_bw_except_last = tf.slice(output_state_bw, [0, 0, 0, 0], [-1, height-1, -1, -1])
        output_state_bw_only_last = tf.slice(output_state_bw, [0, height-1, 0, 0], [-1, 1, -1, -1])
        dummy_zeros = tf.zeros_like(output_state_bw_only_last)
        output_state_bw_with_first_zeros = tf.concat([dummy_zeros, output_state_bw_except_last], 1)
        outputs = output_state_fw + output_state_bw_with_first_zeros
        return outputs

class RowLSTMCell(core_rnn_cell.RNNCell):
  def __init__(self, num_units, kernel_shape=[3, 1]):
    self._num_units = num_units
    self._state_size = num_units * 2
    self._output_size = num_units
    self._kernel_shape = kernel_shape

  @property
  def state_size(self):
    return self._state_size

  @property
  def output_size(self):
    return self._output_size

  def __call__(self, inputs, state, scope="RowLSTMCell"):
    raise Exception("Not implemented")


#----- Convolutions for RNN ------#
def conv2dRNN(inputs, input_dim, output_dim, filter_size, mask_type=None, scope='conv2d', he_init=False):
    '''
        inputs.shape: (batch_size, height, width, input_dim)
        mask_type: None, 'a', 'b'
        output.shape: (batch_size, height, width, output_dim)
    '''
    with tf.variable_scope(scope):
        def uniform(stdev, size):
            """uniform distribution with the given stdev and size"""
            return np.random.uniform(
                low=-stdev * np.sqrt(3),
                high=stdev * np.sqrt(3),
                size=size
            ).astype(np.float32)
        filter_shape = [filter_size, filter_size, input_dim, output_dim]
        filter_init = uniform(
            1./np.sqrt(input_dim * filter_size * filter_size),
            filter_shape
        )
        if he_init:
            filter_init *= np.sqrt(2.)
        filter_init *= np.sqrt(2.)
        filter_w = tf.Variable(filter_init, name='filter_weights')
        filter_b_init = np.zeros(output_dim, dtype=np.float32)
        filter_b = tf.Variable(filter_b_init, name='filter_bias')
    
        if mask_type is not None:
            mask = np.ones(filter_shape, dtype=np.float32)
            center = filter_size // 2
            mask[center, center+1:, :, :] = 0.
            mask[center+1:, :, :, :] = 0.
            if mask_type == 'a':
                mask[center, center, :, :] = 0.
            filter_w = tf.multiply(filter_w, mask)

        print(scope+'_inputs:', inputs.shape)
        outputs = tf.nn.conv2d(inputs, filter_w, [1,1,1,1], padding='SAME', name = 'conv_weights')
        print(scope+'_outputs:', outputs.shape)
        outputs = tf.nn.bias_add(outputs, filter_b, name='conv_bias')
        print(scope+'_outputs1:', outputs.shape)
        return outputs

def conv1dRNN(inputs, input_dim, output_dim, filter_size, user_bias = True, scope='conv1d'):
    '''
        inputs.shape: (batch_size, height, 1, input_dim)
        outputs.shape: (batch_size, height, 1, output_dim)
    '''
    with tf.variable_scope(scope):
        def uniform(stdev, size):
            """uniform distribution with the given stdev and size"""
            return np.random.uniform(
                low=-stdev * np.sqrt(3),
                high=stdev * np.sqrt(3),
                size=size
            ).astype(np.float32)
        filter_shape = [filter_size, 1, input_dim, output_dim]
        filter_w_init = uniform(
            1./np.sqrt(input_dim * filter_size),
            filter_shape)
        filter_w = tf.Variable(filter_w_init, name='filter_weights')
        outputs = tf.nn.conv2d(inputs, filter_w, [1,1,1,1], padding='SAME', name = 'conv_weights')
        if user_bias:
            #filter_b = tf.get_variable('filter_bias', shape=[output_dim], initializer = tf.constant_initializer(0))
            filter_b_init = np.zeros(output_dim, dtype=np.float32)
            filter_b = tf.Variable(filter_b_init, name='filter_bias')
            outputs = tf.nn.bias_add(outputs, filter_b, name='conv_bias')
        return outputs