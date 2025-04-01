#include <hls_x_complex.h>
#include <ap_int.h>

#define N 8192

extern "C" {
void cmpx_conv(hls::x_complex<float> A[N],
               hls::x_complex<float> B[N],
               hls::x_complex<float> C[N]) {
    // AXI master interface for each array
    #pragma HLS INTERFACE mode=m_axi port=A depth=N offset=slave bundle=gmem
    #pragma HLS INTERFACE mode=s_axilite port=A bundle=control

    #pragma HLS INTERFACE mode=m_axi port=B depth=N offset=slave bundle=gmem
    #pragma HLS INTERFACE mode=s_axilite port=B bundle=control

    #pragma HLS INTERFACE mode=m_axi port=C depth=N offset=slave bundle=gmem
    #pragma HLS INTERFACE mode=s_axilite port=C bundle=control

    // Control interface
    #pragma HLS INTERFACE mode=s_axilite port=return bundle=control

    // Compute circular convolution:
    // C[n] = sum_{k=0}^{N-1} A[k] * B[(n-k) mod N]
    for (int n = 0; n < N; n++) {
        #pragma HLS PIPELINE II=1
        hls::x_complex<float> sum = hls::x_complex<float>(0, 0);
        for (int k = 0; k < N; k++) {
            int j = n - k;
            if (j < 0)
                j += N;  // Wrap-around for circular convolution
            sum += A[k] * B[j];
        }
        C[n] = sum;
    }
}
}
