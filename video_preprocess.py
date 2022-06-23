import math

from mail_mandler import MailHandler
import dtlpy as dl
import subprocess
import logging
import json

logger = logging.getLogger(__name__)
NUM_TRIES_COMMAND = 1
NUM_TRIES_FUNC = 3


class VideoPreprocess(dl.BaseServiceRunner):

    @staticmethod
    def execute_cmd(cmd, progress: dl.Progress = None, nb_frames=None):
        exception = ''
        progress_conv = 10
        for _ in range(NUM_TRIES_COMMAND):
            if progress is not None and nb_frames is not None:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                while proc.poll() is None:
                    line = proc.stdout.readline()
                    if progress is not None:
                        if 'frame=' in line:
                            frames = int(line.split('=')[1].split('f')[0].strip())
                            if frames / nb_frames >= progress_conv / 100:
                                progress.update(progress=progress_conv)
                                progress_conv += 10
            else:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            outs, errs = proc.communicate()

            if proc.returncode == 0:
                # if success return the result
                logger.debug(outs)
                return outs
            else:
                # if fail - keep error and try again
                exception += 'stderr:{}'.format(errs)
        # if all tries fail - raise the exception
        raise Exception(exception)

    def _extract_metadata(self, item_stream, with_headers=False):
        # why -b:v & -crf ?
        if with_headers:
            cmd = ['ffprobe',
                   '-select_streams',
                   'v:0',
                   '-count_frames',
                   '-count_packets',
                   '-show_format',
                   '-show_streams',
                   '-of',
                   'json',
                   '-headers',
                   "{}:{}".format('authorization', dl.client_api.auth['authorization']),
                   item_stream]
        else:
            # without headers
            cmd = ['ffprobe',
                   '-select_streams',
                   'v:0',
                   '-count_frames',
                   '-count_packets',
                   '-show_format',
                   '-show_streams',
                   '-of',
                   'json',
                   item_stream]

        return self.execute_cmd(cmd=cmd)

    @staticmethod
    def _duration_str_to_sec(time_str):
        """Get Seconds from time."""
        if time_str is None:
            return None
        try:
            h, m, s = time_str.split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            logger.exception("Got unsupported time_str: {!r}".format(time_str))
            return None

    def metadata_extractor_from_ffmpeg(self, stream, with_headers):

        outs = self._extract_metadata(
            item_stream=stream,
            with_headers=with_headers
        )

        probe_result = json.loads(outs.decode('utf-8'))
        video_stream = next((stream for stream in probe_result['streams'] if stream['codec_type'] == 'video'), None)

        nb_streams = probe_result.get('format', {}).get('nb_streams', 1)

        if video_stream is None:
            raise ValueError('missing video stream for: {}'.format(stream))

        start_time = video_stream.get('start_time', None)
        start_time = eval(start_time) if start_time is not None else 0

        height = video_stream.get('height', None)
        width = video_stream.get('width', None)

        fps = video_stream.get('avg_frame_rate', None)
        fps = eval(fps) if fps is not None else None

        nb_frames = video_stream.get('nb_frames', None)
        nb_frames = eval(nb_frames) if nb_frames is not None else None

        nb_read_frames = video_stream.get('nb_read_frames', None)
        nb_read_frames = eval(nb_read_frames) if nb_read_frames is not None else None

        if 'duration' not in video_stream:
            tags = video_stream.get("tags", dict())
            duration = VideoPreprocess._duration_str_to_sec(tags.get("DURATION", None))
        else:
            duration = video_stream.get('duration', None)
            duration = eval(duration) if duration is not None else None

        if duration is None:
            video_format = probe_result.get('format', dict())
            duration = video_format.get('duration', None)

        res_dict = {
            'ffmpeg': video_stream,
            'start_time': start_time,
            'height': height,
            'width': width,
            'fps': fps,
            'duration': float(duration) if duration is not None else None,
            'nb_read_frames': nb_read_frames,
            'nb_streams': nb_streams
        }
        if nb_frames is not None:
            res_dict['nb_frames'] = nb_frames
        return res_dict

    def validate_video(self, fps, duration, r_frames, default_start_time=0, prefix_check='web'):
        if fps and duration and r_frames:
            if default_start_time is None:
                default_start_time = 0
            exp_frames_count = fps * float(int((duration - default_start_time) * 100)) / 100
            rounded = round(exp_frames_count)
            rounded_up = (math.floor(exp_frames_count) + 1)

            if rounded == rounded_up or rounded == r_frames:
                exp_frames = rounded
            else:
                exp_frames = rounded_up

            if exp_frames != r_frames and abs(exp_frames_count - r_frames) > 0.5:
                return False, exp_frames, self.error_dict(err_type=prefix_check + 'ExpectedFrames',
                                                          err_message='Frames is not equal to FPS * Duration',
                                                          err_value=abs(exp_frames_count - r_frames),
                                                          service_name='VideoPreprocess')
            return True, exp_frames, {}
        else:
            return True, 0, {}

    def error_dict(self, err_type, err_message, err_value, service_name):
        return {
            'type': err_type,
            'message': err_message,
            'value': err_value,
            'service': service_name
        }

    def _metadata_extractor_write_to_item(self, item: dl.Item, metadata):
        # add data
        if 'system' not in item.metadata:
            item.metadata['system'] = dict()
        if 'ffmpeg' in metadata:
            item.metadata['system']['ffmpeg'] = metadata['ffmpeg']
        if 'start_time' in metadata:
            item.metadata['system']['startTime'] = metadata['start_time']
            # backward compatibility
            item.metadata['startTime'] = item.metadata['system']['startTime']
        if 'height' in metadata:
            item.metadata['system']['height'] = metadata['height']
        if 'width' in metadata:
            item.metadata['system']['width'] = metadata['width']
        if 'fps' in metadata:
            item.metadata['system']['fps'] = metadata['fps']
            # backward compatibility
            item.metadata['fps'] = item.metadata['system']['fps']
        if 'duration' in metadata:
            item.metadata['system']['duration'] = metadata['duration']  # will be verified after webm conversion
        if 'nb_frames' in metadata:
            item.metadata['system']['nb_frames'] = metadata['nb_frames']  # will be verified after webm conversion
        if 'nb_streams' in metadata:
            item.metadata['system']['nb_streams'] = metadata['nb_streams']  # will be verified after webm conversion

        r_frames = metadata.get('nb_read_frames', None)
        if r_frames is None:
            r_frames = metadata.get('nb_frames', None)

        validate, exp_frames, validate_msg = self.validate_video(fps=metadata.get('fps', None),
                                                                 duration=metadata.get('duration', None),
                                                                 r_frames=r_frames,
                                                                 default_start_time=metadata.get('start_time', None),
                                                                 prefix_check='orig')
        if not validate:
            self.update_item_errors(item=item, error_dicts=validate_msg)
        return item.update(system_metadata=True)

    def update_item_errors(self, item: dl.Item, error_dicts):
        if not isinstance(error_dicts, list):
            error_dicts = [error_dicts]
        if 'system' not in item.metadata:
            item.metadata['system'] = {}
        if 'errors' not in item.metadata['system']:
            item.metadata['system']['errors'] = []
        for err_dict in error_dicts:
            add_err = True
            for err_index in range(len(item.metadata['system']['errors'])):
                if item.metadata['system']['errors'][err_index]['type'] == err_dict['type']:
                    item.metadata['system']['errors'][err_index] = err_dict
                    add_err = False
            if add_err:
                item.metadata['system']['errors'].append(err_dict)
        item.update(True)

    def metadata_extractor(self, item):
        """
        Extract ffmpeg metadata and write it to item

        :param item: dl.Item
        :return:
        """
        exception = ''
        for _ in range(NUM_TRIES_FUNC):
            try:
                with_headers = True
                item_stream = item.stream
                try:
                    item_stream = item.system['shebang']['linkInfo']['ref']
                    with_headers = False
                except KeyError:
                    # item in not link
                    pass
                metadata = self.metadata_extractor_from_ffmpeg(stream=item_stream, with_headers=with_headers)
                item = self._metadata_extractor_write_to_item(item=item, metadata=metadata)
                if 'errors' in item.metadata['system'] and len(item.metadata['system']['errors']) > 0:
                    continue

                missing = [key for key, val in metadata.items() if not val and key != 'start_time']
                if len(missing) != 0:
                    self.mail_handler.send_alert(
                        item=item,
                        msg=['missing metadata values for item: {}'.format(item.id), missing]
                    )
                    raise Exception('missing metadata values for item: {}'.format(item.id), missing)
                return item
            except Exception as e:
                exception = e
                continue
        if exception != '':
            raise Exception(exception)
        else:
            return item
