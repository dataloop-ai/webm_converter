import pandas as pd
import dtlpy as dl

import logging
import shutil
import time
import csv
import os
import io

from video_preprocess import VideoPreprocess
from webm_converter import ConversionMethod, WebmConverter

logging.basicConfig()
logger = logging.getLogger(name=__name__)
logger.setLevel('DEBUG')


def calculate_timestamp(frame, fps):
    return time.strftime('%H:%M:%S:{}'.format(str(int(frame / fps * 1000) % 1000).zfill(3)),
                         time.gmtime(int(frame / fps * 1000) / 1000.0))


class TimeFrame:
    """
    calculate timestamp from frame and fps

    """

    def __init__(self, frame: int, fps: float):
        self.frame = frame
        self.fps = fps

    @property
    def timestamp(self):
        return calculate_timestamp(frame=self.frame, fps=self.fps)

    @property
    def seconds(self):
        return self.frame / self.fps


class SingleTrim:
    """
    Single trim information
    """

    def __init__(self, name, start: TimeFrame, end: TimeFrame, is_exist=False):
        self.start = start
        self.end = end
        self.is_exist = is_exist
        self.name = name
        if start.frame > end.frame or start.fps != end.fps:
            raise ValueError(" start frame {} is bigger then end frame {}".format(start.frame, end.frame))

        if start.fps != end.fps:
            raise ValueError(" start fps {} is different then end frame {}".format(start.fps, end.fps))

    @property
    def nb_frames(self):
        return self.end.frame - self.start.frame

    @property
    def fps(self):
        return self.start.fps

    @property
    def duration(self):
        return float(self.nb_frames / self.fps)

    @property
    def duration_timestamp(self):
        return calculate_timestamp(frame=self.nb_frames, fps=self.fps)


class TrimsList:
    def __init__(self, orig_filepath, origin_fps, origin_nb_frames, trims_dir, method):
        self.orig_filepath = orig_filepath
        self.trims_dir = trims_dir
        self.method = method
        self.orig_fps = origin_fps
        self.origin_nb_frames = origin_nb_frames
        self.list = list()
        self.current = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.current += 1
        if self.current < len(self):
            return self.list[self.current]
        raise StopIteration

    def append(self, item):
        self.list.append(item)

    def __getitem__(self, item):
        return self.list[item]

    def __len__(self):
        return len(self.list)

    def not_existing_files(self):
        return [trim for trim in self.list if not trim.is_exist]


class TrimVideo(dl.BaseServiceRunner):
    """
    Plugin runner class

    """

    def __init__(self):
        self.video_handler = VideoPreprocess()

    def get_fps_and_nb_frames(self, item):
        fps = nb_frames = None
        with_headers = False
        stream = item
        if isinstance(item, dl.Item):
            with_headers = True
            stream = item.stream
            fps = item.fps
            nb_frames = item.system.get('nb_frames', None)
            if not nb_frames:
                nb_frames = item.system.get('ffmpeg', dict()).get('nb_read_frames', None)
                if nb_frames:
                    nb_frames = int(nb_frames)

        if not fps or not nb_frames:
            trim_metadata = self.video_handler.metadata_extractor_from_ffmpeg(stream=stream, with_headers=with_headers)
            fps = trim_metadata['fps']
            nb_frames = trim_metadata.get('nb_frames', None)
            if not nb_frames:
                nb_frames = trim_metadata['nb_read_frames']

        return fps, nb_frames

    def trimming_results_report(self, item):
        file_dir = item.metadata.get('system', dict()).get('trim', dict()).get('destinationPath', None)
        if file_dir is None:
            file_dir, ext = os.path.splitext(item.filename)

        origin_fps = item.metadata.get('system', dict()).get('fps', None)
        if not origin_fps:
            origin_fps, _ = self.get_fps_and_nb_frames(item=item)
        origin_file_name = item.name

        trimmed_dataset_id = item.metadata.get('system', dict()).get('trim', dict()).get('destinationDatasetId', None)
        expected_trim_files = item.metadata.get('system', dict()).get('trim', dict()).get('expectedTrimFiles', None)

        if trimmed_dataset_id is None:
            trimmed_dataset = item.dataset
        else:
            trimmed_dataset = item.project.datasets.get(dataset_id=trimmed_dataset_id)

        filters = dl.Filters(field='dir', values=file_dir)
        filters.add(field='metadata.system.mimetype', values="*video*")
        filters.sort = {'name': dl.FILTERS_ORDERBY_DIRECTION_ASCENDING}
        pages = trimmed_dataset.items.list(filters=filters)
        print("Found {} files".format(pages.items_count))
        results = dict()

        trim_success = True if expected_trim_files == pages.items_count else False
        for page in pages:
            for trimmed_item in page:
                system = trimmed_item.metadata.get('system', dict())
                nb_frames = system.get('nb_frames', None)
                if not nb_frames:
                    nb_frames = system.get('ffmpeg', dict()).get('nb_read_frames', None)
                    if nb_frames:
                        nb_frames = int(nb_frames)
                fps = system.get('fps', None)
                if fps is None or nb_frames is None:
                    fps, nb_frames = self.get_fps_and_nb_frames(item=item)

                trim = system.get('trim', dict())
                start_from = trim.get('startFrom', None)
                end_on = trim.get('endOn', None)
                origin_file_name = trim.get('originalVideo', "NA")
                origin_file_id = trim.get('originalVideoId', "NA")
                before_overlapping = trim.get('beforeOverlapping', 0)
                after_overlapping = trim.get('afterOverlapping', "NA")
                original_nb_frames = None
                if start_from is not None and end_on is not None:
                    original_nb_frames = end_on - start_from + 1

                delta_nb_frames = None
                if nb_frames is not None and original_nb_frames is not None:
                    delta_nb_frames = original_nb_frames - nb_frames

                if (fps != origin_fps) or delta_nb_frames or nb_frames is None:
                    trim_success = False

                results[trimmed_item.id] = {'Item Name': trimmed_item.name,
                                            'Item Dir': trimmed_item.dir,
                                            'Item ID': trimmed_item.id,
                                            'FPS': fps,
                                            'Origin FPS': origin_fps,
                                            'Origin File Name': origin_file_name,
                                            'Origin File Id': origin_file_id,
                                            'NB Frames': nb_frames,
                                            'Calculated NB Frame': original_nb_frames,
                                            'Delta NB Frames': delta_nb_frames,
                                            'Start From': start_from,
                                            'End On': end_on,
                                            'Before Overlapping': before_overlapping,
                                            'After Overlapping': after_overlapping}

        df = pd.DataFrame(list(results.values()),
                          columns=['Item Name', 'Item Dir', 'Item ID',
                                   'FPS', 'Origin FPS',
                                   'Origin File Name', 'Origin File Id',
                                   'NB Frames', 'Calculated NB Frame', 'Delta NB Frames',
                                   'Start From', 'End On',
                                   'Before Overlapping', 'After Overlapping'])

        if trim_success and len(results):
            csv_file_name = '{}_report.csv'.format(origin_file_name)
        else:
            csv_file_name = '{}_report_error.csv'.format(origin_file_name)

        csv_bin = io.BytesIO()
        csv_bin.write(df.to_csv(index=False, line_terminator='\n').encode())
        trimmed_dataset.items.upload(local_path=csv_bin,
                                     remote_path=file_dir,
                                     remote_name=csv_file_name,
                                     overwrite=True)

        if origin_file_name == item.name:
            item.metadata['system']['trim']['report'] = "Succeeded" if trim_success else "Failed"
            item.update(system_metadata=True)

        if trim_success:
            return item

    @staticmethod
    def write_trim_list(output_csv_file, trims_list: TrimsList):
        with open(output_csv_file, 'wt') as file:
            csv_writer = csv.writer(file, lineterminator='\n')
            # If required, output the cutting list as the first row (i.e. before the header row).
            csv_writer.writerow(["Timecode List:"] + [single_trim.start.timestamp for single_trim in trims_list])
            csv_writer.writerow([
                "Scene Number",
                "Start Frame", "Start Timecode", "Start Time (seconds)",
                "End Frame", "End Timecode", "End Time (seconds)",
                "Length (frames)", "Length (timecode)", "Length (seconds)"])
            for i, single_trim in enumerate(trims_list.list):
                csv_writer.writerow('{},{},{},{:.3f},{},{},{:.3f},{},{},{:.3f}'.format(i + 1,
                                                                                       single_trim.start.frame,
                                                                                       single_trim.start.timestamp,
                                                                                       single_trim.start.seconds,
                                                                                       single_trim.end.frame,
                                                                                       single_trim.end.timestamp,
                                                                                       single_trim.end.seconds,
                                                                                       single_trim.nb_frames,
                                                                                       single_trim.duration_timestamp,
                                                                                       single_trim.duration).split(','))

    def trims_list_to_webm(self, trims_list: TrimsList, progress, retries=2):
        log_header = '[preprocess][trimming-video][{func}]'.format(func='trims_list_to_webm')
        if not len(trims_list):
            return None

        video_handler = WebmConverter(method=trims_list.method)

        logger.info('{} Going to trim {} files out from {}'.format(log_header,
                                                                   len(trims_list.not_existing_files()),
                                                                   len(trims_list)))
        if not len(trims_list):
            return None

        try:
            tic = time.time()
            for single_trim in trims_list.not_existing_files():
                for retry in range(retries):
                    trim_filepath = os.path.join(trims_list.trims_dir, single_trim.name)
                    logger.info("{} {} trim {!r} is starting, retry {}".format(
                        log_header, trims_list.method, single_trim.name, retry + 1))
                    if trims_list.method == ConversionMethod.FFMPEG:
                        video_handler.convert_to_webm(input_filepath=trims_list.orig_filepath,
                                                      output_filepath=trim_filepath,
                                                      fps=trims_list.orig_fps,
                                                      start_time=single_trim.start.seconds,
                                                      duration=single_trim.duration)
                    else:
                        raise NotImplementedError("Method {} not supported".format(trims_list.method))
                    fps, nb_frames = self.get_fps_and_nb_frames(trim_filepath)

                    if nb_frames == single_trim.nb_frames:
                        break
                    logger.info("{} {} trim {!r} has {} NB while calculated video has {} NB retry {}".format(
                        log_header, trims_list.method, single_trim.name, nb_frames, single_trim.nb_frames, retry + 1))
                    time.sleep(5)
                if progress:
                    # 96 is  the % between 3 -> 99 used progress for this part
                    progress.update(
                        status='Trimming {}/{}'.format(single_trim.start.frame, trims_list.origin_nb_frames),
                        progress=round(single_trim.start.frame / trims_list.origin_nb_frames * 96))
            duration = time.time() - tic
            logger.info(
                '{header} converted with {method}. conversion took: {dur}[s]'.format(
                    header=log_header,
                    method=trims_list.method,
                    dur=duration))

        except OSError:
            logger.exception('ffmpeg could not be found on the system.'
                             ' Please install ffmpeg to enable video output support.')

    def calculate_trims(self, trims_list: TrimsList, destination_dataset, remote_trims_path,
                        is_sec, number_of_frames, before_overlapping, after_overlapping):

        ext = ".webm"
        orig_file_name = os.path.basename(trims_list.orig_filepath)
        fps = trims_list.orig_fps
        nb_frames = trims_list.origin_nb_frames

        if is_sec:
            number_of_frames = int(number_of_frames * fps)
            before_overlapping = int(before_overlapping * fps)
            after_overlapping = int(after_overlapping * fps)

        logger.debug("calculate_trims: fps= {}, number of frames = {}".format(nb_frames, number_of_frames))
        total_trim = int(nb_frames / number_of_frames)
        pad = len(str(total_trim))

        start_from = 0
        end_on = number_of_frames
        trim_num = 0
        filters = dl.Filters(field='dir', values=remote_trims_path)
        items = [item for item in destination_dataset.items.list(filters=filters).all()]

        while start_from < nb_frames:
            trim_file_name = '{}-trim-{}{}'.format(orig_file_name, str(trim_num).zfill(pad), ext)
            trim_item = None
            try:
                trim_item = [item for item in items if item.filename == remote_trims_path + '/' + trim_file_name][0]
            except IndexError:
                pass
            if trim_item:
                trim_fps, trim_nb_frames = self.get_fps_and_nb_frames(item=trim_item)
                trim_start_from = start_from - before_overlapping if start_from else 0
                end_and_overlapping = end_on + after_overlapping
                trim_end_on = end_and_overlapping if end_and_overlapping < nb_frames else nb_frames
                if trim_item.annotated or (trim_fps == fps and trim_nb_frames == trim_end_on - trim_start_from):
                    logger.debug("Existing: {} ".format(trim_item.name))
                    trim_num += 1
                    trims_list.append(SingleTrim(name=trim_file_name,
                                                 start=TimeFrame(frame=trim_start_from, fps=fps),
                                                 end=TimeFrame(frame=trim_end_on, fps=fps),
                                                 is_exist=True))
                    start_from += number_of_frames
                    end_on += number_of_frames
                    continue
                else:
                    logger.debug("Existing: {} but corrupted origin fps {} while trim fps {} "
                                 "and origin nb frames {} while trim nb frames {}".format(trim_item.name, fps,
                                                                                          trim_fps,
                                                                                          trim_end_on - trim_start_from,
                                                                                          trim_nb_frames))
                    trim_item.delete()

            trims_list.append(SingleTrim(
                name=trim_file_name,
                start=TimeFrame(frame=start_from - before_overlapping if start_from else 0, fps=fps),
                end=TimeFrame(frame=end_on + after_overlapping if trim_num != total_trim else nb_frames, fps=fps)))

            start_from += number_of_frames
            end_on += number_of_frames
            trim_num += 1

        return trims_list

    def video_trimming_by_seconds(self, item: dl.Item, progress=None,
                                  number_of_seconds=None, before_overlapping=0, after_overlapping=0,
                                  destination_dataset_name=None, main_dir='/'):
        return self.video_trimming(item=item, is_sec=True,
                                   number_of_frames=number_of_seconds,
                                   before_overlapping=before_overlapping, after_overlapping=after_overlapping,
                                   destination_dataset_name=destination_dataset_name, main_dir=main_dir,
                                   progress=progress)

    def video_trimming_by_frames(self, item: dl.Item, progress=None,
                                 number_of_frames=None, before_overlapping=0, after_overlapping=0,
                                 destination_dataset_name=None, main_dir='/'):
        return self.video_trimming(item=item, is_sec=False,
                                   number_of_frames=number_of_frames,
                                   before_overlapping=before_overlapping, after_overlapping=after_overlapping,
                                   destination_dataset_name=destination_dataset_name, main_dir=main_dir,
                                   progress=progress)

    def video_trimming(self, item: dl.Item, progress=None,
                       is_sec=False, number_of_frames=None, before_overlapping=0, after_overlapping=0,
                       destination_dataset_name=None, main_dir='/',
                       method: ConversionMethod = ConversionMethod.FFMPEG):

        # Default parameters in case of pipeline
        if is_sec is None:
            is_sec = False
        if number_of_frames is None:
            number_of_frames = 60 * 120
        if before_overlapping is None:
            before_overlapping = 0
        if after_overlapping is None:
            after_overlapping = 0
        if main_dir and main_dir[0] != "/":
            main_dir = "/" + main_dir
        if method is None:
            method = ConversionMethod.FFMPEG

        return self._video_trimming(item=item, progress=progress, is_sec=is_sec, number_of_frames=number_of_frames,
                                    before_overlapping=before_overlapping, after_overlapping=after_overlapping,
                                    destination_dataset_name=destination_dataset_name, main_dir=main_dir,
                                    method=method)

    def _video_trimming(self, item: dl.Item, progress=None,
                        is_sec=False, number_of_frames=None, before_overlapping=0, after_overlapping=0,
                        destination_dataset_name=None, main_dir='/',
                        method: ConversionMethod = ConversionMethod.FFMPEG):

        if destination_dataset_name is not None:
            try:
                destination_dataset = item.project.datasets.get(dataset_name=destination_dataset_name)
            except dl.exceptions.NotFound:
                destination_dataset = item.project.datasets.create(dataset_name=destination_dataset_name)
        else:
            destination_dataset = item.dataset

        workdir = item.id

        log_header = '[preprocess][trimming-video][{item_id}][{func}]'.format(item_id=item.id, func='video_trimming')

        logger.info('{} Video trimming has been started item {}, '
                    'is_sec {}, number_of_frames {}, before_overlapping {}, after_overlapping {}, '
                    'main_dir {!r}, destination dataset {!r}'.format(log_header,
                                                                     item.id,
                                                                     is_sec,
                                                                     number_of_frames,
                                                                     before_overlapping,
                                                                     after_overlapping,
                                                                     main_dir,
                                                                     destination_dataset.name))
        if progress:
            progress.update(status='Downloading video', progress=1)

        try:
            orig_filepath = os.path.join(workdir, item.name)
            logger.info('{header} downloading item'.format(header=log_header))
            orig_filepath = item.download(local_path=orig_filepath, overwrite=True)

            orig_file_name, _ = os.path.splitext(item.name)

            trims_dir = os.path.join(workdir, 'trims', orig_file_name)
            os.makedirs(trims_dir, exist_ok=True)

            # remote_trims_path = item.dir + "/" + orig_file_name if len(item.dir) > 1 else item.dir + orig_file_name
            # remote_trims_path = main_dir + remote_trims_path if main_dir and main_dir != "" else remote_trims_path

            if main_dir and main_dir != "":
                if main_dir[0] != '/':
                    main_dir = '/' + main_dir
                remote_trims_path = main_dir + item.dir.rstrip('/') + "/" + orig_file_name

            else:
                remote_trims_path = item.dir.rstrip('/') + "/" + orig_file_name

            trims_list_path = os.path.join(trims_dir, '{}-trim.csv'.format(orig_file_name))

            if progress:
                progress.update(status='Find scenes', progress=2)

            fps, nb_frames = self.get_fps_and_nb_frames(orig_filepath)

            trims_list = TrimsList(orig_filepath=orig_filepath,
                                   origin_fps=fps,
                                   origin_nb_frames=nb_frames,
                                   trims_dir=trims_dir,
                                   method=method)

            trims_list = self.calculate_trims(trims_list=trims_list,
                                              destination_dataset=destination_dataset,
                                              remote_trims_path=remote_trims_path,
                                              is_sec=is_sec,
                                              number_of_frames=number_of_frames,
                                              before_overlapping=before_overlapping,
                                              after_overlapping=after_overlapping)

            logger.info('{} item {} {} calculate {} trims'.format(log_header, item.id, item.name, len(trims_list)))

            item.metadata['system']['trim'] = {"destinationDatasetId": destination_dataset.id,
                                               'destinationPath': remote_trims_path,
                                               'status': 'In Progress',
                                               'expectedTrimFiles': len(trims_list)}
            item = item.update(system_metadata=True)

            if progress:
                progress.update(status='Trimming...', progress=3)

            self.trims_list_to_webm(trims_list=trims_list, progress=progress)

            if progress:
                progress.update(status='Uploading trimmed files', progress=99)

            self.write_trim_list(output_csv_file=trims_list_path, trims_list=trims_list)

            for video_file in os.listdir(trims_dir):
                file, ext = os.path.splitext(video_file)
                if ext != '.csv':
                    idx = int(file.split("-")[-1])
                    converted_before_overlapping = before_overlapping if not is_sec else \
                        int(before_overlapping / trims_list.orig_fps)
                    converted_after_overlapping = after_overlapping if not is_sec else \
                        int(after_overlapping / trims_list.orig_fps)
                    item_metadata = {"system": {"trim": {"originalVideo": item.name,
                                                         "originalVideoId": item.id,
                                                         "originalVideoDatasetId": item.dataset.id,
                                                         "method": method,
                                                         "expectedTrimFiles": len(trims_list),
                                                         "trimNumber": int(file.split("-")[-1]),
                                                         "startFrom": trims_list[idx].start.frame,
                                                         "endOn": trims_list[idx].end.frame - 1,
                                                         "beforeOverlapping": converted_before_overlapping,
                                                         "afterOverlapping": converted_after_overlapping}}}
                    uploaded_item = destination_dataset.items.upload(local_path=os.path.join(trims_dir, video_file),
                                                                     remote_path=remote_trims_path,
                                                                     item_metadata=item_metadata)
                else:
                    uploaded_item = destination_dataset.items.upload(local_path=os.path.join(trims_dir, video_file),
                                                                     remote_path=remote_trims_path,
                                                                     overwrite=True)
                logger.info("Uploaded {} {}-".format(uploaded_item.filename, uploaded_item.id))

            item.metadata['system']['trim']['status'] = "Done"
            item = item.update(system_metadata=True)

            return item.id
        except Exception as r:
            logger.exception("{} item {} {} - ERROR: ".format(log_header, item.id, item.name, r))
        finally:
            if workdir:
                shutil.rmtree(workdir)


def test():
    trim_runner = TrimVideo()
    item = dl.items.get(item_id='61ed6a946c58a6684ea87402')
    trim_runner.video_trimming_by_frames(item=item,
                                         number_of_frames=50,
                                         before_overlapping=5,
                                         main_dir='results_trim_videos')

    trim_runner.trimming_results_report(item=item)


if __name__ == "__main__":
    test()
