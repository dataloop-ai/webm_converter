#include <iostream> // for standard I/O
#include <string>   // for strings

#include <opencv2/core.hpp>    // Basic OpenCV structures (cv::Mat)
#include <opencv2/videoio.hpp> // Video write
#include <chrono>

using namespace std;
using namespace cv;

int main(int argc, char *argv[])
{
    auto t1 = std::chrono::high_resolution_clock::now();
    auto t2 = std::chrono::high_resolution_clock::now();
    const string source = argv[1];
    const string NAME = argv[2];  // Form the new name with container

    VideoCapture inputVideo(source); // Open input
    if (!inputVideo.isOpened())
    {
        cout << "Could not open the input video: " << source << endl;
        return -1;
    }
    int ex = static_cast<int>(808996950);             // Get Codec Type- Int form

    Size S = Size((int)inputVideo.get(CAP_PROP_FRAME_WIDTH), // Acquire input size
                  (int)inputVideo.get(CAP_PROP_FRAME_HEIGHT));

    VideoWriter outputVideo; // Open the output
    outputVideo.open(NAME, ex, inputVideo.get(CAP_PROP_FPS), S, true);

    if (!outputVideo.isOpened())
    {
        cout << "Could not open the output video for write: " << source << endl;
        return -1;
    }

    Mat src;

    for (;;) //Show the image captured in the window and repeat
    {
        inputVideo >> src; // read
        if (src.empty())
        {
            break;
        } // check if at end
        outputVideo << src;
    }
    t2 = std::chrono::high_resolution_clock::now();
    std::cout << " runs took "
              << float(std::chrono::duration_cast<std::chrono::milliseconds>(t2 - t1).count())  / float(1000)
              << " seconds\n";
    return 0;
}
