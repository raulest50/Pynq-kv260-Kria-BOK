#include <hls_stream.h>
#include <ap_int.h>

#define N 8192

extern "C" {
void array_gain(float input[N], float output[N], float gain) {
#pragma HLS INTERFACE mode=m_axi port=input depth=N offset=slave bundle=gmem
#pragma HLS INTERFACE mode=s_axilite port=input  bundle=control

#pragma HLS INTERFACE mode=m_axi port=output depth=N offset=slave bundle=gmem
#pragma HLS INTERFACE mode=s_axilite port=output bundle=control

#pragma HLS INTERFACE mode=s_axilite port=gain   bundle=control
#pragma HLS INTERFACE mode=s_axilite port=return bundle=control

    for (int i = 0; i < N; i++) {
        #pragma HLS PIPELINE II=1
        output[i] = input[i] * gain;
    }

}
}
