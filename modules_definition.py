from typing import List

import dtlpy as dl


def get_webm_modules() -> List[dl.PackageModule]:
    return [
        dl.PackageModule(
            name='webm_module',
            class_name='WebmConverter',
            entry_point='webm_converter.py',
            functions=[
                dl.PackageFunction(
                    inputs=[dl.FunctionIO(type="Item", name="item")],
                    outputs=[],
                    name='run',
                    description='Webm converter'),
            ]
        )
    ]
