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
                    description='Webm converter'),
            ]
        )
    ]


def get_trim_modules() -> List[dl.PackageModule]:
    return [
        dl.PackageModule(
            name='trim_module',
            class_name='TrimVideo',
            entry_point='trim_video.py',
            functions=[
                dl.PackageFunction(
                    inputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item"),
                            dl.FunctionIO(type=dl.PackageInputType.INT, name="number_of_frames"),
                            dl.FunctionIO(type=dl.PackageInputType.INT, name="before_overlapping"),
                            dl.FunctionIO(type=dl.PackageInputType.INT, name="after_overlapping"),
                            dl.FunctionIO(type=dl.PackageInputType.STRING, name="destination_dataset_name"),
                            dl.FunctionIO(type=dl.PackageInputType.STRING, name="main_dir")],
                    outputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item")],
                    name='video_trimming_by_frames',
                    description='Trim video by number of frames'),
                dl.PackageFunction(
                    inputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item"),
                            dl.FunctionIO(type=dl.PackageInputType.INT, name="number_of_seconds"),
                            dl.FunctionIO(type=dl.PackageInputType.INT, name="before_overlapping"),
                            dl.FunctionIO(type=dl.PackageInputType.INT, name="after_overlapping"),
                            dl.FunctionIO(type=dl.PackageInputType.STRING, name="destination_dataset_name"),
                            dl.FunctionIO(type=dl.PackageInputType.STRING, name="main_dir")],
                    outputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item")],
                    name='video_trimming_by_seconds',
                    description='Trim video by number of seconds'),
                dl.PackageFunction(
                    inputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item")],
                    outputs=[dl.FunctionIO(type=dl.PackageInputType.ITEM, name="item")],
                    name='trimming_results_report',
                    description='Generate report after trimming')
            ]
        )
    ]
