from flow_workflow.commands.launch_base import LaunchWorkflowCommandBase
from flow.configuration.inject.local_broker import BrokerConfiguration
from flow.configuration.inject.redis_conf import RedisConfiguration
from flow.configuration.inject.service_locator import ServiceLocatorConfiguration
from flow.orchestrator.handlers import PetriCreateTokenHandler
from flow.orchestrator.handlers import PetriNotifyPlaceHandler
from flow.orchestrator.handlers import PetriNotifyTransitionHandler
from flow.shell_command.fork.handler import ForkShellCommandMessageHandler
from twisted.internet import defer


class ExecuteWorkflowCommand(LaunchWorkflowCommandBase):
    injector_modules = [
            BrokerConfiguration,
            RedisConfiguration,
            ServiceLocatorConfiguration,
    ]

    local_workflow = True

    def setup_services(self, net):
        self.setup_shell_command_handlers()
        self.setup_orchestrator_handlers()

        self.setup_completion_handler(net)

    def setup_shell_command_handlers(self):
        self.broker.register_handler(
                self.injector.get(ForkShellCommandMessageHandler))

    def setup_orchestrator_handlers(self):
        self.broker.register_handler(
                self.injector.get(PetriCreateTokenHandler))
        self.broker.register_handler(
                self.injector.get(PetriNotifyPlaceHandler))
        self.broker.register_handler(
                self.injector.get(PetriNotifyTransitionHandler))

    @defer.inlineCallbacks
    def wait_for_results(self, block):
        yield self.broker.listen()
        defer.returnValue(True)
