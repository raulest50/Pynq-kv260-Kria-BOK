#include <hls_x_complex.h>
#include <ap_int.h>

#define DIM 48

extern "C" {
void cmpx_mat_product(
                 hls::x_complex<float> Ma[DIM][DIM],
                 hls::x_complex<float> Mb[DIM][DIM],
                 hls::x_complex<float> Mc[DIM][DIM]
                 ) {
    // AXI master interfaces for each matrix
    #pragma HLS INTERFACE mode=m_axi port=Ma depth=2304 offset=slave bundle=gmem
    #pragma HLS INTERFACE mode=s_axilite port=Ma bundle=control

    #pragma HLS INTERFACE mode=m_axi port=Mb depth=2304 offset=slave bundle=gmem
    #pragma HLS INTERFACE mode=s_axilite port=Mb bundle=control

    #pragma HLS INTERFACE mode=m_axi port=Mc depth=2304 offset=slave bundle=gmem
    #pragma HLS INTERFACE mode=s_axilite port=Mc bundle=control

    // Control interface
    #pragma HLS INTERFACE mode=s_axilite port=return bundle=control

    // Compute matrix multiplication:
    // Mc[i][j] = sum_{k=0}^{DIM-1} Ma[i][k] * Mb[k][j]
    for (int i = 0; i < DIM; i++) {
        // Optionally pipeline the outer loop (adjust II as needed)
        //#pragma HLS PIPELINE II=1
        for (int j = 0; j < DIM; j++) {
            hls::x_complex<float> sum = hls::x_complex<float>(0, 0);
            for (int k = 0; k < DIM; k++) {
                sum += Ma[i][k] * Mb[k][j];
            }
            Mc[i][j] = sum;
        }
    }
}
}
