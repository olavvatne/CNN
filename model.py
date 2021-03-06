from abc import ABCMeta, abstractmethod
import theano
import theano.tensor as T
from elements import HiddenLayer, ConvPoolLayer, OutputLayer
import numpy as np
import math
from collections import deque

class AbstractModel(object):
    '''
    Different architectures inherit from AbstractModel. Contains methods needed by the Evaluator class.
    The abstract build method should be implemented by subclasses.
    '''
    __metaclass__ = ABCMeta

    def __init__(self, params, verbose):
        #Every layer appended to this variable. layer 0= input, layer N = output
        self.layer= []
        self.L2_layers = []
        self.rng = np.random.RandomState(params.random_seed)
        self.input_data_dim = params.input_data_dim
        self.hidden = params.hidden_layer
        self.output_label_dim = params.output_label_dim
        self.model_config = params


    def get_output_layer(self):
        assert len(self.layer) >0
        return self.layer[-1]


    def get_cost(self, y, factor=1):
        return  self.get_output_layer().negative_log_likelihood(y, factor)


    def get_errors(self, y):
        self.get_output_layer().errors(y)


    def _weight(self, params, idx):
        if not params:
            return None
        return params[idx]


    def create_predict_function(self, x, drop, data):
        return theano.function([data], self.get_output_layer().output,
                   givens={x: data, drop: np.cast['int32'](int(False))})


    def getL2(self):
        v = 0
        for layer in self.layer:
            v += T.sum(layer.W ** 2)
        return v


    @abstractmethod
    def build(self, x, batch_size, init_params=None):
        return



class ShallowModel(AbstractModel):

    def __init__(self, params, verbose=False):
        super(ShallowModel, self).__init__(params, verbose)

    def build(self, x, batch_size, init_params=None):
        print('Shallow neural network model')
        channels, width, height = self.input_data_dim
        layer0 = HiddenLayer(
            self.rng,
            input=x,
            n_in=channels*width*height,
            n_out=2048,
            activation=T.nnet.relu,
            W=self._weight(init_params, 2),
            b=self._weight(init_params, 3)
        )

        layer1 = OutputLayer(
            self.rng,
            input=layer0.output,
            n_in=2048,
            n_out=256,
            W=self._weight(init_params, 0),
            b=self._weight(init_params, 1),
            batch_size=batch_size
        )

        self.L2_layers = [layer0, layer1]
        self.layer = [layer0, layer1]
        self.params =  layer1.params + layer0.params
        print('Model created!')


class ConvModel(AbstractModel):
    '''
    The ConvModel builds the architecture based on the values found in the config file, or stored params.pkl file.
    The buld method dynamically creates the convolutional layers from the config specification. However the
    fully connected layers are static. The final hidden layer is fully connected as well as the output layer.
    the specification of the config. If there are init params, the layers are initialized from these values. Otherwise,
    each layer's weights and biases are initialized by random values.
    '''

    def __init__(self, params, verbose=True):
        super(ConvModel, self).__init__(params, verbose)
        self.nr_kernels = params.nr_kernels
        self.dropout_rate = params.dropout_rates
        self.conv = params.conv_layers
        #Because of for loop -1 will disappear, but keep queue len being 2.
        self.queue = deque([self.input_data_dim[0], -1])
        self.verbose = verbose

    def _get_filter(self, next_kernel, filter):
        self.queue.appendleft(next_kernel)
        self.queue.pop()
        return list(self.queue) + list(filter)


    def build(self, x, drop, batch_size, init_params=None):

        print('Creating layers for convolutional neural network model')
        if self.verbose and init_params:
            print('---- Using supplied weights and bias')

        channels, width, height = self.input_data_dim
        layer_input = x.reshape((batch_size, channels, width, height))

        #See model for explanation
        p_len = 0
        if init_params:
            p_len = len(init_params)

        inp_shape = (batch_size, channels, width, height)

        for i in range(len(self.conv)):
            init_idx = p_len - (i*2)-1

            filter = self._get_filter(self.nr_kernels[i], self.conv[i]["filter"])
            layer = ConvPoolLayer(
                self.rng,
                input=layer_input,
                image_shape=inp_shape,
                filter_shape=filter,
                strides=self.conv[i]["stride"],
                poolsize=self.conv[i]["pool"],
                activation=T.nnet.relu(x),
                W=self._weight(init_params, init_idx-1),
                b=self._weight(init_params, init_idx),
                drop=drop,
                dropout_rate=self.dropout_rate[i],
                verbose=self.verbose
            )

            layer_input = layer.output
            dim_x = self.get_output_length(inp_shape[2], self.conv[i]["filter"][0],  self.conv[i]["pool"][0], self.conv[i]["stride"][0], 0 )
            dim_y = self.get_output_length(inp_shape[3], self.conv[i]["filter"][1],  self.conv[i]["pool"][1], self.conv[i]["stride"][1], 0 )
            #dim_x = int(math.floor((inp_shape[2] - self.conv[i]["filter"][0] +1) / (self.conv[i]["stride"][0] * self.conv[i]["pool"][0])))
            #dim_y = int(math.floor((inp_shape[3] - self.conv[i]["filter"][1] +1) / (self.conv[i]["stride"][1] * self.conv[i]["pool"][1])))
            print(dim_x, dim_y)

            inp_shape = (batch_size, self.nr_kernels[i], dim_x, dim_y)
            self.layer.append(layer)

        hidden_input = self.layer[-1].output.flatten(2)
        print(self.nr_kernels[-1], inp_shape[2], inp_shape[3])
        # construct a fully-connected sigmoidal layer
        hidden_layer = HiddenLayer(
            self.rng,
            input=hidden_input,
            n_in=self.nr_kernels[-1] * inp_shape[2] * inp_shape[3],
            n_out=self.hidden,
            activation=T.nnet.relu(x),
            W=self._weight(init_params, 2),
            b=self._weight(init_params, 3),
            drop=drop,
            dropout_rate=self.dropout_rate[-2],
            verbose=self.verbose

        )

        output_dim = self.output_label_dim[0] * self.output_label_dim[1]
        output_layer = OutputLayer(
            self.rng,
            input=hidden_layer.output,
            n_in=self.hidden,
            n_out=output_dim,
            W=self._weight(init_params, 0),
            b=self._weight(init_params, 1),
            loss=  self.model_config.loss,
            batch_size=batch_size,
            verbose=self.verbose
        )

        self.L2_layers = [hidden_layer, output_layer]
        self.layer.extend(self.L2_layers)
        self.params = []
        for layer in reversed(self.layer):
            self.params += layer.params

        print('Model created!')

    def get_output_length(self, input_length, filter_size, pool_size, stride, pad):
        output_length = input_length - filter_size + 1
        output_length = (output_length + stride - 1) // stride
        print(output_length)
        overlap = False
        if not overlap:
            #Pooling with no overlap - and ignore border which exclude pooling regions outside input border.
            output_length = int(np.floor(output_length / pool_size))
        else:
            output_length = output_length - pool_size + 1
        print(output_length)
        return output_length