import behave
import os
from webm_converter import WebmConverter


@behave.when(u'I upload a file in path "{item_local_path}"')
def step_impl(context, item_local_path):
    item_local_path = os.path.join(os.environ["DATALOOP_TEST_ASSETS"], item_local_path)
    context.item = context.dataset.items.upload(local_path=item_local_path,
                                                remote_path=None
                                                )


@behave.then(u'item is clean')
def step_impl(context):
    item = context.dl.items.get(item_id=context.item.id)
    assert 'modalities' not in item.metadata['system']
    assert 'errors' not in item.metadata['system']


@behave.then(u'i run a converter in it')
def step_impl(context):
    WebmConverter().run(context.item)


@behave.then(u'i delete the project')
def step_impl(context):
    context.project.delete(True, True)


@behave.then(u'i check the item success')
def step_impl(context):
    item = context.dl.items.get(item_id=context.item.id)
    assert len(item.metadata['system']['modalities']) > 0


@behave.then(u'i check the item fail')
def step_impl(context):
    item = context.dl.items.get(item_id=context.item.id)
    assert len(item.metadata['system']['errors']) > 0
