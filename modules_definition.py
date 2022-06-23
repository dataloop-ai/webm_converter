from typing import List

import dtlpy as dl


def get_webm_modules() -> List[dl.PackageModule]:
    return [
        dl.PackageModule(
            name='webm_module',
            class_name='WebmConverter',
            entry_point='webm_converter.py',
            init_inputs=[dl.FunctionIO(type=dl.PackageInputType.STRING, name="method")],
            functions=[
                dl.PackageFunction(
                    inputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item")],
                    outputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item")],
                    name='run',
                    description='Run Webm converter on input item, except method as param, possible values: ffmpeg, opencv. default to ffmpeg'),
            ]
        )
    ]
