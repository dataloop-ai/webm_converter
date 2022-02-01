import dtlpy as dl
import os

from modules_definition import get_webm_modules

package_name = 'webm_converter-converter'
project_name = 'projectName'

project = dl.projects.get(project_name=project_name)

###############
#   package   #
###############

# for first package push
module = get_webm_modules()[0]

package = project.packages.push(
    package_name=package_name,
    modules=[module],
    src_path=os.getcwd()
)

package = project.packages.get(package_name=package_name)

###########
# service #
###########
# deploy for new service creation
service = package.services.deploy(
    service_name=package_name,
    execution_timeout=2 * 60 * 60,
    module_name=module.name,
    runtime=dl.KubernetesRuntime(
        concurrency=1,
        pod_type=dl.InstanceCatalog.REGULAR_M,
        runner_image='gcr.io/viewo-g/piper/agent/cpu/webm_converter:4',
        autoscaler=dl.KubernetesRabbitmqAutoscaler(
            min_replicas=1,
            max_replicas=100,
            queue_length=2
        )
    )
)

service = project.services.get(service_name=package.name.lower())

if package.version != service.package_revision:
    service.package_revision = package.version
    service = service.update(True)

#########################
# new trigger creation #
#######################

triggers = service.triggers.list()
if triggers.items_count != 1:
    raise Exception('Triggers count is other than 1')
trigger = triggers.items[0]

trigger = project.triggers.create(
    name=package.name,
    scope='system',
    service_id=service.id,
    execution_mode=dl.TriggerExecutionMode.ONCE,
    resource='Item',
    actions=['Updated'],
    filters={
        '$and': [
            {
                'metadata.system.mimetype': {
                    '$eq': 'video*'
                }
            },
            {
                'metadata.system.size': {
                    '$lt': 1073741824
                }
            },
            {
                'metadata.system.mimetype': {
                    '$ne': 'video/webm_converter'
                }
            },
            {
                "metadata.system.fps": {
                    "$gt": 0
                }
            },
            {
                "hidden": False
            },
            {
                "type": "file"
            }
        ]
    }
)
