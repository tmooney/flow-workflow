#!/usr/bin/env python

from collections import defaultdict
from flow.orchestrator.graph import transitive_reduction
from xml.dom.minidom import parseString
import flow_workflow.nodes as wfnodes
import json
import os
import re
import sys

from flow.orchestrator.types import *

MAX_FILENAME_LEN = 30
WORKFLOW_WRAPPER = 'workflow-wrapper'


class WorkflowEntity(object):
    def __init__(self, job_number):
        self.job_number = job_number

    def node(self, redis, flow_key):
        raise NotImplementedError("node not implemented in %s" %
                                  self.__class__.__name__)


class WorkflowOperation(WorkflowEntity):

    def __init__(self, job_number, xml):
        WorkflowEntity.__init__(self, job_number)

        self.name = xml.attributes["name"].nodeValue
        self.job_number = job_number

        type_nodes = xml.getElementsByTagName("operationtype")
        if len(type_nodes) != 1:
            raise RuntimeError(
                "Wrong number of <operationtype> tags in operation %s" % name
            )

        self._type_node = type_nodes[0]
        self._operation_attributes = dict(xml.attributes.items())
        self._type_attributes = dict(self._type_node.attributes.items())


class CommandOperation(WorkflowOperation):
    def __init__(self, job_number, log_dir, xml):
        WorkflowOperation.__init__(self, job_number, xml)
        self.perl_class = self._type_attributes['commandClass']
        self._set_log_files(log_dir)

        self.parallel_by = ""
        if "parallelBy" in self._operation_attributes:
            self.parallel_by = self._operation_attributes["parallelBy"]

    def _set_log_files(self, log_dir):
        basename = re.sub("[^A-Za-z0-9_.-]", "_", self.name)[:MAX_FILENAME_LEN]
        out_file = "%d-%s.out" %(self.job_number, basename)
        err_file = "%d-%s.err" %(self.job_number, basename)
        self.stdout_log_file = os.path.join(log_dir, out_file)
        self.stderr_log_file = os.path.join(log_dir, err_file)

    def node(self, redis, flow_key):
        if self.parallel_by:
            return wfnodes.ParallelByCommandFlow.create(
                    connection=redis,
                    flow_key=flow_key,
                    perl_class=self.perl_class,
                    stdout_log_file=self.stdout_log_file,
                    stderr_log_file=self.stderr_log_file,
                    parallel_by_property=self.parallel_by,
                    name = self.name,
                    )
        else:
            return wfnodes.CommandNode.create(
                    connection=redis,
                    flow_key=flow_key,
                    perl_class=self.perl_class,
                    stdout_log_file=self.stdout_log_file,
                    stderr_log_file=self.stderr_log_file,
                    name = self.name,
                    )


class ConvergeOperation(WorkflowOperation):
    def __init__(self, job_number, log_dir, xml):
        WorkflowOperation.__init__(self, job_number, log_dir, xml)

        inputs = self.type_node.getElementsByTagName("inputproperty")
        self.input_properties = [x.firstChild.nodeValue for x in inputs]
        output = self.type_node.getElementsByTagName("outputproperty")
        if len(output) != 1:
            raise RuntimeError(
                "Wrong number of <outputproperty> tags in operation %s"
                %name)
        self.output_name = output[0].firstChild.nodeValue

    def node(self, redis, flow_key):
        return wfnodes.ConvergeNode(
                connection=redis,
                flow_key=flow_key,
                input_property_order=self.input_properties,
                output_property=self.output_property,
                name = self.name,
                )


class InputConnector(WorkflowEntity):
    def __init__(self, job_number, outputs):
        WorkflowEntity.__init__(self, job_number)
        self.name = "input connector"
        self.outputs = outputs

    def node(self, redis, flow_key):
        return StartNode.create(connection=redis, flow_key=flow_key,
                                name="start node", outputs=self.outputs)


class OutputConnector(WorkflowEntity):
    def __init__(self, job_number):
        WorkflowEntity.__init__(self, job_number)
        self.name = "output connector"

    def node(self, redis, flow_key):
        return StopNode.create(connection=redis, flow_key=flow_key,
                               name="stop node")

class Parser(object):
    input_connector_id = 0
    output_connector_id = 1
    first_operation_id = 2

    operation_types = {
        "Workflow::OperationType::Command" : CommandOperation,
        "Workflow::OperationType::Converge": ConvergeOperation,
    }

    def __init__(self, xml, initial_inputs):
        self.dom = parseString(xml)
        self.operations = [
            InputConnector(job_number=self.input_connector_id, outputs=initial_inputs),
            OutputConnector(job_number=self.output_connector_id),
        ]
        self.edges = defaultdict(set)
        self.input_connections = defaultdict(lambda: defaultdict(dict))

        root_tag_name = self.dom.documentElement.tagName
        root_tag_actions = {
            "workflow": self._parse_workflow,
            "operation": self._parse_workflow_simple
        }

        if root_tag_name not in root_tag_actions:
            raise RuntimeError(
                "Root element is <%s>, expected <workflow> or <operation>"
                %rootTagName
                )

        self.rootAttr = self.dom.documentElement.attributes
        self.wf_name = self.rootAttr["name"].nodeValue
        self.log_dir = "."
        if self.rootAttr.has_key("logDir"):
            self.log_dir = self.rootAttr["logDir"].nodeValue

        root_tag_actions[root_tag_name]()
        self.edges = transitive_reduction(self.edges)
        self.rev_edges = {}
        for src, dst_set in self.edges.iteritems():
            print src, dst_set
            for dst in dst_set:
                self.rev_edges.setdefault(dst, set()).add(src)

    def _parse_workflow_simple(self):
        self._parse_operations()
        # We expect input/output connectors, and a single operation
        if len(self.operations) != 3:
            raise RuntimeError("Simple workflow with more than a single operation!")

        self.input_connections[self.first_operation_id][self.input_connector_id] = {}
        self.add_edge(self.input_connector_id, self.first_operation_id)
        self.add_edge(self.first_operation_id, self.output_connector_id)

    def _parse_workflow(self):
        self._parse_operations()
        self._parse_links()

    def _parse_operations(self):
        for operation_node in self.dom.getElementsByTagName("operation"):
            self._add_operation(operation_node)

    def add_edge(self, src_idx, dst_idx):
        if src_idx == dst_idx:
            raise RuntimeError("Attempted to create self cycle with node %d" %src_idx)

        self.edges[src_idx].add(dst_idx)

    def _parse_links(self):
        op_indices = dict(((x.name, x.job_number) for x in self.operations))
        for link in self.dom.getElementsByTagName("link"):
            src = link.attributes["fromOperation"].nodeValue
            dst = link.attributes["toOperation"].nodeValue
            src_idx = op_indices[src]
            dst_idx = op_indices[dst]

            src_prop = link.attributes["fromProperty"].nodeValue
            dst_prop = link.attributes["toProperty"].nodeValue

            self.add_edge(src_idx, dst_idx)

            self.input_connections[dst_idx][src_idx][dst_prop] = src_prop

    def _add_operation(self, operation_node):
        optype_tags = operation_node.getElementsByTagName("operationtype")
        if len(optype_tags) != 1:
            raise RuntimeError("Wrong number of <operationtype> subtags in operation %s" %name)
        optype = optype_tags[0]
        type_class = optype.attributes["typeClass"].nodeValue

        if type_class not in self.operation_types:
            raise RuntimeError("Unknown operation type %s in workflow xml" %type_class)

        idx = len(self.operations)
        op = self.operation_types[type_class](
            job_number=idx,
            xml=operation_node,
            log_dir=self.log_dir
            )
        self.operations.append(op)

    def flow(self, redis):
        flow = Flow.create(connection=redis, name=self.wf_name)

        nodes = [op.node(redis, flow.key) for op in self.operations]

        for idx, op in enumerate(self.operations):
            node = nodes[idx]
            if idx in self.edges:
                node.successors = self.edges[idx]
            else:
                node.successors = set()

        for dst_idx, props in self.input_connections.iteritems():
            store = dict((k, json.dumps(v)) for k, v in props.iteritems())
            nodes[dst_idx].input_connections = store

        for idx, node in enumerate(nodes):
            if idx in self.rev_edges:
                node.indegree = len(self.rev_edges[idx])

        flow.node_keys = [n.key for n in nodes]
        return flow


if __name__ == "__main__":
    import flow.orchestrator.redisom as rom
    import subprocess

    class FakeCommandLineService(object):
        def __init__(self, conn):
            self.conn = conn

        def submit(self, cmdline, return_identifier=None, executor_options=None):
            cmdline = map(str, cmdline)
            print "EXEC", cmdline
            services = {
                    wfnodes.GENOME_SHORTCUT_SERVICE: self,
                    wfnodes.GENOME_EXECUTE_SERVICE: self,
                    }
            rv = subprocess.call(cmdline)
            if rv == 0:
                callback = return_identifier['on_success']
            else:
                callback = return_identifier['on_failure']

            rom.invoke_instance_method(self.conn, callback, services=services,
                                       return_identifier=return_identifier)


    import redis
    import sys
    if len(sys.argv) != 2:
        print "Give filename!"
        sys.exit(1)

    xml = open(sys.argv[1]).read()
    inputs = {
        "a": '"BQcKC29wZXJhdGlvbiBB\\n"',
        "b": '"BQcKC29wZXJhdGlvbiBC\\n"',
        "c": '"BQcKC29wZXJhdGlvbiBD\\n"',
        "d": '"BQcKC29wZXJhdGlvbiBE\\n"',
    }
    p = Parser(xml, inputs)
    print p.edges
    print "Ops"
    redis = redis.Redis()
    flow = p.flow(redis)
    services = {
        wfnodes.GENOME_SHORTCUT_SERVICE: FakeCommandLineService(redis),
        wfnodes.GENOME_EXECUTE_SERVICE: FakeCommandLineService(redis),
    }
    flow.node(0).execute(services)
