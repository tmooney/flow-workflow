from flow.petri_net.actions.base import BasicActionBase
from flow_workflow.io import load
from flow_workflow.io import store
from twisted.internet import defer

import logging


LOG = logging.getLogger(__name__)


# This function mimics legacy Workflow's strange "Converge" operation.
# It 'converges' all outputs into one with the name of the first output_property
def order_outputs(inputs, input_property_order, output_properties):
    out_list = [inputs[x] for x in input_property_order]
    outputs = {
            output_properties[0]: out_list,
            'result':1,
    }
    return outputs


class GenomeConvergeAction(BasicActionBase):
    required_arguments =["operation_id", 'input_connections',
            "input_property_order", "output_properties"]

    def execute(self, net, color_descriptor, active_tokens, service_interfaces):
        operation_id = self.args["operation_id"]

        input_property_order = self.args["input_property_order"]
        output_properties = self.args["output_properties"]


        workflow_data = load.extract_data_from_tokens(active_tokens)
        parallel_idx = workflow_data['parallel_idx']
        inputs = io.load_input(net=net, input_connections=input_connections,
                parallel_idx=parallel_idx)

        outputs = order_outputs(inputs, input_property_order, output_properties)

        io.store_outputs(net=net, operation_id=operation_id,
                outputs=outputs, parallel_idx=parallel_idx)

        data = {'workflow_data':workflow_data}
        output_token = net.create_token(color=color_descriptor.color,
                color_group_idx=color_descriptor.group.idx,
                data=workflow_data)

        return [output_token], defer.succeed(None)