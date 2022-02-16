import dtlpy as dl

from modules_definition import get_trim_modules

package_name = 'custom-video-trimming'
project_name = 'projectName'


project = dl.projects.get(project_name=project_name)

###############
#   package   #
###############

# for first package push
module = get_trim_modules()[0]

# # build package use source code
# import os
# package = project.packages.push(
#     package_name=package_name,
#     modules=[module],
#     service_config={
#         'runtime': dl.KubernetesRuntime(
#             concurrency=1,
#             pod_type=dl.InstanceCatalog.REGULAR_M,
#             runner_image='gcr.io/viewo-g/piper/agent/cpu/webm:4',
#             autoscaler=dl.KubernetesRabbitmqAutoscaler(
#                 min_replicas=0,
#                 max_replicas=10,
#                 queue_length=1
#             )).to_json()},
#     src_path=os.getcwd()
# )

# build package use GIT repo
package = project.packages.push(
    # is_global=True,
    package_name=package_name,
    modules=[module],
    service_config={
        'runtime': dl.KubernetesRuntime(
            concurrency=1,
            pod_type=dl.InstanceCatalog.REGULAR_M,
            runner_image='gcr.io/viewo-g/piper/agent/cpu/webm:4',
            autoscaler=dl.KubernetesRabbitmqAutoscaler(
                min_replicas=0,
                max_replicas=10,
                queue_length=1
            )).to_json()},
    codebase=dl.GitCodebase(git_url='https://github.com/dataloop-ai/webm_converter.git', git_tag='v1.0.0')
)

# package = project.packages.get(package_name=package_name)

###########
# service #
###########
# # # no need to install the serive on DatasloopApps
# # deploy for new service creation
# service = package.services.deploy(
#     service_name=package_name,
#     execution_timeout=5 * 60 * 60,
#     module_name=module.name,
# )
#
# service = project.services.get(service_name=package.name.lower())
#
# if package.version != service.package_revision:
#     service.package_revision = package.version
#     service = service.update(True)

