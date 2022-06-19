import random

import attr
import behave
import time
import jwt
import os
import dtlpy as dl
import numpy as np

dl.verbose.disable_progress_bar = True


@attr.s
class TimeKey:
    # For TestRail test-run
    _key = None

    @property
    def key(self):
        if self._key is None:
            self._key = time.strftime("%d-%m %H:%M")
        return self._key


time_key = TimeKey()


@behave.given('Platform Interface is initialized as dlp and Environment is set according to git branch')
def before_all(context):
    # set up lists to delete
    if not hasattr(context, 'to_delete_projects_ids'):
        context.to_delete_projects_ids = list()
    if not hasattr(context, 'to_delete_pipelines_ids'):
        context.to_delete_pipelines_ids = list()
    if hasattr(context.feature, 'dataloop_feature_dl'):
        context.dl = context.feature.dataloop_feature_dl
    else:
        # get cookie name
        feature_name = context.feature.name.replace(' ', '_')
        api_counter_name = 'api_counter_{}.json'.format(feature_name)
        api_counter_filepath = os.path.join(os.path.dirname(dl.client_api.cookie_io.COOKIE), api_counter_name)
        # set counter
        dl.client_api.set_api_counter(api_counter_filepath)

        # set context for run
        context.dl = dl

        # reset api counter
        context.dl.client_api.calls_counter.on()
        context.dl.client_api.calls_counter.reset()

        # check token
        payload = None
        for i in range(10):
            try:
                payload = jwt.decode(context.dl.token(), algorithms=['HS256'],
                                     verify=False, options={'verify_signature': False})
                break
            except jwt.exceptions.DecodeError:
                time.sleep(np.random.rand())
                pass

        if payload['email'] not in ['oa-test-4@dataloop.ai',
                                    'oa-test-1@dataloop.ai',
                                    'oa-test-2@dataloop.ai',
                                    'oa-test-3@dataloop.ai',
                                    'mohamed@dataloop.ai']:
            assert False, 'Cannot run test on user: "{}". only test users'.format(payload['email'])

        # save to feature level
        context.feature.dataloop_feature_dl = context.dl


@behave.given('There is a project by the name of "{project_name}"')
def step_impl(context, project_name):
    if hasattr(context.feature, 'dataloop_feature_project'):
        context.project = context.feature.dataloop_feature_project
    else:
        num = random.randint(10000, 100000)
        project_name = 'to-delete-test-{}_{}'.format(str(num), project_name)
        context.project = context.dl.projects.create(project_name=project_name)
        context.to_delete_projects_ids.append(context.project.id)
        context.feature.dataloop_feature_project = context.project
        time.sleep(5)
    context.dataset_count = 0


@behave.given('There is a dataset by the name of "{dataset_name}"')
def step_impl(context, dataset_name):
    if hasattr(context.feature, 'dataloop_feature_dataset'):
        context.dataset = context.feature.dataloop_feature_dataset
    else:
        num = random.randint(10000, 100000)
        dataset_name = 'to-delete-test-{}_{}'.format(str(num), dataset_name)
        context.dataset = context.project.datasets.create(dataset_name=dataset_name)
        context.feature.dataloop_feature_dataset = context.dataset
        time.sleep(5)
