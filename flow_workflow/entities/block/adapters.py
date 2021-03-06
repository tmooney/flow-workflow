from flow_workflow.pass_through import future_nets
import flow_workflow.adapter_base


class BlockAdapter(flow_workflow.adapter_base.XMLAdapterBase):
    operation_class = 'pass_through'


    def future_net(self, resources):
        return future_nets.PassThroughNet(name=self.name,
                operation_id=self.operation_id)
