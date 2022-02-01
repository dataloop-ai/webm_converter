FROM gcr.io/viewo-g/piper/agent/runner/cpu/main:1.39.2.0

RUN apt update
RUN yes | add-apt-repository ppa:jonathonf/ffmpeg-4
RUN apt install ffmpeg -y

RUN apt-get update
RUN apt update
RUN yes | add-apt-repository "deb http://security.ubuntu.com/ubuntu xenial-security main"
RUN apt update
RUN apt install libjasper1 libjasper-dev

RUN apt-get update && \
        apt-get install -y \
        build-essential \
        cmake \
        git \
        wget \
        unzip \
        yasm \
        pkg-config \
        libswscale-dev \
        libtbb2 \
        libtbb-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libjasper-dev \
        libavformat-dev \
        libpq-dev


WORKDIR /
RUN wget https://github.com/opencv/opencv_contrib/archive/3.2.0.zip \
&& unzip 3.2.0.zip \
&& rm 3.2.0.zip

RUN wget https://github.com/Itseez/opencv/archive/3.2.0.zip \
&& unzip 3.2.0.zip \
&& mkdir /opencv-3.2.0/cmake_binary

RUN cd /opencv-3.2.0 \
&& sed -i '1 i\#define AVFMT_RAWPICTURE 0x0020' modules/videoio/src/cap_ffmpeg_impl.hpp \
&& sed -i '1 i\#define CODEC_FLAG_GLOBAL_HEADER AV_CODEC_FLAG_GLOBAL_HEADER' modules/videoio/src/cap_ffmpeg_impl.hpp \
&& sed -i '1 i\#define AV_CODEC_FLAG_GLOBAL_HEADER (1 << 22)' modules/videoio/src/cap_ffmpeg_impl.hpp

RUN cd /opencv-3.2.0/cmake_binary \
&& cmake -DBUILD_TIFF=ON \
  -DBUILD_opencv_java=OFF \
  -DOPENCV_EXTRA_MODULES_PATH=/opencv_contrib-3.2.0/modules \
  -DWITH_FFMPEG=ON \
  -DWITH_CUDA=OFF \
  -DENABLE_AVX=ON \
  -DWITH_OPENGL=ON \
  -DWITH_OPENCL=ON \
  -DWITH_IPP=ON \
  -DWITH_TBB=ON \
  -DWITH_EIGEN=ON \
  -DWITH_V4L=ON \
  -DBUILD_TESTS=OFF \
  -DBUILD_PERF_TESTS=OFF \
  -DCMAKE_BUILD_TYPE=RELEASE \
  -DCMAKE_INSTALL_PREFIX=$(python3.6 -c "import sys; print(sys.prefix)") \
  -DPYTHON_EXECUTABLE=$(which python3.6) \
  -DPYTHON_INCLUDE_DIR=$(python3.6 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
  -DPYTHON_PACKAGES_PATH=$(python3.6 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") .. \
&& make install \
&& rm /3.2.0.zip \
&& rm -r /opencv-3.2.0 \
&& rm -r /opencv_contrib-3.2.0

RUN pip install flake8 pep8 --upgrade