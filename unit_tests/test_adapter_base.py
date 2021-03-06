from lxml import etree

import mock
import unittest
import flow_workflow.adapter_base


VALID_XML = '''
<operation name="test_op_name">
    <operationtype commandClass="NullCommand"
                   typeClass="Workflow::OperationType::Command" />
</operation>
'''

INVALID_XML = '''
<operation name="duplicate_operation_types">
    <operationtype commandClass="NullCommand"
                   typeClass="Workflow::OperationType::Command" />
    <operationtype commandClass="NullCommand"
                   typeClass="Workflow::OperationType::Command" />
</operation>
'''


class FakeAdapter(flow_workflow.adapter_base.XMLAdapterBase):
    operation_class = 'fake'

    def future_net(self, **kwargs):
        return flow_workflow.adapter_base.XMLAdapterBase.future_net(self,
                **kwargs)


class ValidAdapterBaseTest(unittest.TestCase):
    def setUp(self):
        self.operation_id = 12345
        self.parent = mock.Mock()

        self.adapter = FakeAdapter(xml=etree.XML(VALID_XML),
                operation_id=self.operation_id,
                parent=self.parent)


    def test_name(self):
        self.assertEqual('test_op_name', self.adapter.name)

    def test_operation_attributes(self):
        self.assertEqual({'name': 'test_op_name'},
                self.adapter.operation_attributes)

    def test_operation_type_attributes(self):
        self.assertEqual({'commandClass': 'NullCommand',
            'typeClass': 'Workflow::OperationType::Command'},
            self.adapter.operation_type_attributes)


class InvalidAdapterBaseTest(unittest.TestCase):
    def setUp(self):
        self.operation_id = 12345
        self.parent = mock.Mock()

        self.adapter = FakeAdapter(xml=etree.XML(INVALID_XML),
                operation_id=self.operation_id,
                parent=self.parent)

    def test_operation_type_attributes(self):
        with self.assertRaises(ValueError):
            self.adapter.operation_type_attributes


if __name__ == '__main__':
    unittest.main()
