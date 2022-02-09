import traceback
import numpy as np
import dtlpy as dl
import datetime
import logging
import shutil
import time
import cv2
import os
import math

from video_preprocess import VideoPreprocess

logger = logging.getLogger(__name__)
NUM_TRIES = 2


class ConversionMethod:
    FFMPEG = 'ffmpeg'
    OPENCV = 'opencv'


class WebmConverter(dl.BaseServiceRunner):
    """
    Plugin runner class

    """

    def __init__(self, method=ConversionMethod.FFMPEG):
        self.video_handler = VideoPreprocess()
        self.method = method
        if method == ConversionMethod.OPENCV:
            cmd_build_file = ['chmod', '777', 'opencv_converter']
            self.video_handler.execute_cmd(cmd=cmd_build_file)

    def _convert_to_webm_opencv(self, item, filepath, nb_streams):
        """
        Convert the video use opencv
        """
        tic = time.time()
        output_file_path = os.path.join(filepath, '{}.webm'.format(item.id))
        input_file_path = os.path.join(filepath, item.name)

        # start extract the video
        webm_video = str(os.path.join(filepath, 'video.webm'))
        cmd = [
            './opencv_converter',
            '{}?jwt={}'.format(item.stream, dl.token()),
            webm_video
        ]
        self.video_handler.execute_cmd(cmd=cmd)

        # if nb_streams is 2 this mean that the video have an audio
        if nb_streams == 2:
            have_audio = True
            # start extract the audio
            webm_audio = os.path.join(filepath, '{}.aac'.format(item.id))
            try:
                cmd = [
                    'ffmpeg',
                    '-i',
                    input_file_path,
                    '-vn',  # is no video.
                    '-acodec',
                    'copy',  # -acodec copy says use the same audio stream that's already in there.
                    webm_audio
                ]
                self.video_handler.execute_cmd(cmd=cmd)
            except Exception as err:
                if 'does not contain any stream' in str(err):
                    have_audio = False
                    pass
                else:
                    raise err

            # marge video and audio file into one webm file
            if have_audio:
                cmd = [
                    'ffmpeg',
                    '-i',
                    webm_video,
                    '-i',
                    webm_audio,
                    '-c:v',
                    'copy',  # copy video as ot with out encode
                    '-c:a',
                    'libopus',  # encode audio
                    '-map',
                    '0:0',
                    '-map',
                    '1:0',
                    # -map 0:0 -map 1:0 - we map stream 0 (video) from first file, and stream 0 from second file (mp3) to output.
                    output_file_path
                ]
                self.video_handler.execute_cmd(cmd=cmd)
            else:
                os.rename(webm_video, output_file_path)
        else:
            os.rename(webm_video, output_file_path)
        print('time: {:.02f}'.format((time.time() - tic)))

    def convert_to_webm(self, input_filepath,
                        output_filepath,
                        fps,
                        nb_frames=None,
                        progress=None,
                        item=None,
                        workdir=None,
                        nb_streams=1):
        """
        convert the video to webm
        """
        # use FFMPEG
        if self.method == ConversionMethod.FFMPEG:
            self._convert_to_webm_ffmpeg(
                input_filepath=input_filepath,
                output_filepath=output_filepath,
                fps=fps,
                nb_frames=nb_frames,
                progress=progress
            )
        else:
            # use opencv
            self._convert_to_webm_opencv(
                item=item,
                filepath=workdir,
                nb_streams=nb_streams)

    def _convert_to_webm_ffmpeg(self, input_filepath, output_filepath, fps, nb_frames=None, progress=None):
        """
        Convert the video use run a ffmpeg command
        """
        cmds = [
            'ffmpeg',
            # To force the frame rate of the output file
            '-r', str(fps),
            # Item local path / stream
            '-i', input_filepath,
            # Overwrite output files without asking
            '-y',
            # Log level
            '-v', 'info',
            # Duplicate or drop input frames to achieve constant output frame rate fps.
            '-max_muxing_queue_size', '9999',
            output_filepath
        ]
        self.video_handler.execute_cmd(cmd=cmds, nb_frames=nb_frames, progress=progress)

        return

    @staticmethod
    def _upload_webm_item(item, webm_file_path):
        dataset = dl.datasets.get(fetch=False, dataset_id=item.datasetId)
        pre, _ = os.path.splitext(item.filename)
        item_arr = pre.split('/')[:-1]
        item_folder = '/'.join(item_arr)

        remote_path = '/.dataloop/webm{}'.format(item_folder)
        webm_item = dataset.items.upload(
            local_path=webm_file_path,
            remote_path=remote_path,
            overwrite=True
        )

        return webm_item

    @staticmethod
    def _set_item_modality(item, modality_item):
        d = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1)
        now = (d - epoch).total_seconds()
        item.modalities.create(
            modality_type='replace',
            ref=modality_item.id,
            ref_type=dl.MODALITY_REF_TYPE_ID,
            name=modality_item.name,
            timestamp=int(now)
        )
        item.update(system_metadata=True)

    @staticmethod
    def round_duration(number):
        return float(int(number * 100)) / 100

    def verify_webm_conversion(self, webm_filepath: str, orig_metadata: dict):
        """
        verify the webm output if his metadata is match the origin video metadata
        """
        webm_ffprobe = self.video_handler.metadata_extractor_from_ffmpeg(stream=webm_filepath, with_headers=False)

        webm_nb_read_frames = float(webm_ffprobe['nb_read_frames'])
        orig_nb_read_frames = float(orig_metadata['nb_read_frames'])

        webm_fps = webm_ffprobe['fps']
        orig_fps = orig_metadata['fps']

        webm_duration = webm_ffprobe['duration']
        orig_duration = orig_metadata['duration']

        summary = {
            'webm_nb_read_frames': webm_nb_read_frames,
            'orig_nb_read_frames': orig_nb_read_frames,
            'webm_fps': webm_fps,
            'orig_fps': orig_fps,
            'webm_duration': webm_duration,
            'orig_duration': orig_duration
        }

        diff_fps = np.abs(orig_fps - webm_fps)

        if diff_fps < 0.2 and \
                orig_nb_read_frames == webm_nb_read_frames:
            return True, summary
        else:
            return False, summary

    def verify_video_metadata(self, filepath):
        metadata = self.video_handler.metadata_extractor_from_ffmpeg(stream=filepath, with_headers=False)
        n_frames = metadata.get('nb_frames', None)

        if n_frames is None:
            cap = cv2.VideoCapture(filepath)
            n_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        duration = metadata['duration']
        start_time = metadata['start_time']
        fps = metadata['fps']

        if float(start_time) < 0:
            verified = False
            msg = 'negative start time'
        elif n_frames != np.round((duration - start_time) * fps):
            # video metadata is inconsistent
            verified = False
            msg = 'not valued frame number'
        else:
            verified = True
            msg = 'success'
        return verified, {
            'n_frames': n_frames,
            'duration': duration,
            'start_time': start_time,
            'fps': fps,
            'msg': msg
        }, metadata

    def validate_video(self, fps, duration, r_frames):
        exp_frames_count = fps * self.round_duration(duration)
        rounded = round(exp_frames_count)
        rounded_up = (math.floor(exp_frames_count) + 1)

        if rounded == rounded_up or rounded == r_frames:
            exp_frames = rounded
        else:
            exp_frames = rounded_up

        if exp_frames != r_frames and abs(exp_frames_count - r_frames) > 0.5:
            return False, exp_frames, 'invalid frames number should be : {} and it {}'.format(exp_frames, r_frames)
        return True, exp_frames, ''

    def webm_converter(self, item: dl.Item, workdir, progress=None):
        """
        Convert to webm for web

        :param item: dl.Item
        :param workdir: dump path
        :param progress: progress
        :return:
        """
        log_header = '[preprocess][on_create][{item_id}][{func}]'.format(item_id=item.id, func='webm-converter')
        webm_filepath = os.path.join(workdir, '{}.webm'.format(item.id))
        orig_filepath = os.path.join(workdir, item.name)
        orig_filepath = item.download(local_path=orig_filepath)

        # get the item metadata if it in the item else get it from run ffmpeg command
        if 'ffmpeg' not in item.metadata['system']:
            orig_metadata = self.video_handler.metadata_extractor_from_ffmpeg(stream=orig_filepath, with_headers=False)
        else:
            orig_metadata = {
                'ffmpeg': item.metadata['system']['ffmpeg'],
                'start_time': item.metadata['startTime'],
                'height': item.height,
                'width': item.width,
                'fps': item.metadata['fps'],
            }

            if item.metadata['system'].get('duration', None) is not None:
                orig_metadata['duration'] = float(item.metadata['system']['duration'])

            if item.metadata['system']['ffmpeg'].get('nb_read_frames', None) is not None:
                orig_metadata['nb_read_frames'] = int(item.metadata['system']['ffmpeg']['nb_read_frames'])

            if item.metadata['system']['ffmpeg'].get('nb_frames', None) is not None:
                orig_metadata['nb_frames'] = int(item.metadata['system']['ffmpeg']['nb_frames'])

        logger.info('{header} downloading item'.format(header=log_header))

        success = True
        msg = ['item filename: {!r}, id: {!r}'.format(item.filename, item.id)]
        logger.info('{} converting with {}'.format(log_header, self.method))

        tic = time.time()

        # convert the video to webm
        self.convert_to_webm(
            input_filepath=orig_filepath,
            output_filepath=webm_filepath,
            fps=orig_metadata['fps'],
            nb_frames=orig_metadata.get('nb_read_frames', None),
            progress=progress,
            item=item,
            workdir=workdir,
            nb_streams=orig_metadata.get('nb_streams', 1),
        )

        duration = time.time() - tic
        same, summary = self.verify_webm_conversion(
            webm_filepath=webm_filepath,
            orig_metadata=orig_metadata
        )

        # verify the webm output if his metadata is match the origin video metadata
        validate_webm, exp_frames_webm, validate_webm_msg = self.validate_video(summary['webm_fps'],
                                                                                summary['webm_duration'],
                                                                                summary['webm_nb_read_frames'])
        if not validate_webm:
            summary['validate_webm'] = validate_webm_msg
            same = False

        validate_orig, exp_frames_orig, validate_orig_msg = self.validate_video(summary['orig_fps'],
                                                                                summary['orig_duration'],
                                                                                summary['orig_nb_read_frames'])
        if not validate_orig:
            summary['validate_orig'] = validate_orig_msg
            same = False

        if exp_frames_webm != exp_frames_orig:
            summary['expected_frames'] = "webm expected frames do not match the orig {} != {}".format(exp_frames_webm,
                                                                                                      exp_frames_orig)
            same = False

        # add a fail msg to item when the webm not match the original
        if self.round_duration(summary['webm_duration']) != self.round_duration(summary['orig_duration']):
            if 'system' not in item.metadata:
                item.metadata['system'] = {}
            item.metadata['system'][
                'webmConverterWarning'] = 'Webm duration is different than original item duration. {}:{}'.format(
                summary['webm_duration'], summary['orig_duration'])

        logger.info(
            '{header} converted with {method}. conversion took: {dur}[s]'.format(
                header=log_header,
                method=self.method,
                dur=duration
            )
        )

        msg.extend(
            [
                'Webm file and original video are the same? {}'.format(same),
                'conversion with {} took duration: {:.2f}[s]'.format(
                    self.method,
                    duration
                ),
                'webm_n_frames != orig_n_frames, webm_fps != orig_fps',
                '{webm_n_frames} != {orig_n_frames}, {webm_fps} != {orig_fps}'.format(
                    webm_n_frames=summary['webm_nb_read_frames'],
                    orig_n_frames=summary['orig_nb_read_frames'],
                    webm_duration=summary['webm_duration'],
                    orig_duration=summary['orig_duration'],
                    webm_fps=summary['webm_fps'],
                    orig_fps=summary['orig_fps']
                )
            ]
        )

        if same:
            # webm is the same as the original
            logger.info(
                '{header} Original video and webm are same. summary: {summary}. uploading'.format(
                    header=log_header,
                    summary=summary
                )
            )

            # upload web to platform
            webm_item = self._upload_webm_item(
                item=item,
                webm_file_path=webm_filepath
            )

            if not isinstance(webm_item, dl.Item):
                raise Exception('Failed to upload webm')

            # set modality on original
            self._set_item_modality(
                item=item,
                modality_item=webm_item
            )

        else:
            success = False
            logger.warning(
                '{header} orig and webm are NOT same. summary: {summary}'.format(
                    header=log_header,
                    summary=summary
                )
            )

        return success, '{header} orig and webm are NOT same. summary: {summary}'.format(
            header=log_header,
            summary=summary
        )

    def run(self, item: dl.Item, progress=None):
        ##################
        # webm converter #
        ##################
        workdir = None
        success = False
        msg = ''
        try:
            for _ in range(NUM_TRIES):
                try:
                    workdir = item.id
                    os.makedirs(workdir, exist_ok=True)
                    success, msg = self.webm_converter(item=item, workdir=workdir, progress=progress)
                    if success:
                        break
                    else:
                        continue
                except Exception:
                    msg = traceback.format_exc()
                    continue

            if not success:
                raise Exception(msg)
            return item

        except Exception as e:
            raise ValueError('[webm-converter] failed\n error: {}'.format(e))
        finally:
            if workdir is not None and os.path.isdir(workdir):
                shutil.rmtree(workdir)
