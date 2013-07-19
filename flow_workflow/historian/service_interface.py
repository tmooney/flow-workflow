from flow.configuration.settings.injector import setting
from flow_workflow.historian.messages import UpdateMessage
from injector import inject
from twisted.internet import defer

import flow.interfaces
import flow_workflow.interfaces
import logging


LOG = logging.getLogger(__name__)


@inject(broker=flow.interfaces.IBroker,
        exchange=setting('workflow.historian.exchange'),
        routing_key=setting('workflow.historian.routing_key'))
class WorkflowHistorianServiceInterface(flow_workflow.interfaces.IWorkflowHistorian):
    def update(self, net_key, operation_id, color, name, workflow_plan_id, **kwargs):
        if workflow_plan_id < 0:
            # ignore update (don't even make message)
            LOG.debug("Received negative workflow_plan_id:%s, "
                    "ignoring update (net_key=%s, operation_id=%s, color=%s, name=%s,"
                    "workflow_plan_id=%s, kwargs=%s)",
                    workflow_plan_id, net_key, operation_id, color, name,
                    workflow_plan_id, kwargs)
            return defer.succeed(None)
        else:
            LOG.debug("Sending update (net_key=%s, operation_id=%s, color=%s, name=%s,"
                    "workflow_plan_id=%s, kwargs=%s)",
                    net_key, operation_id, color, name, workflow_plan_id, kwargs)
            message = UpdateMessage(net_key=net_key, operation_id=operation_id,
                    color=color, name=name, workflow_plan_id=workflow_plan_id,
                    **kwargs)
            return self.broker.publish(self.exchange, self.routing_key, message)
