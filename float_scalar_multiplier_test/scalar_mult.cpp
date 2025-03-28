// adder_hls.cpp
#include <iostream>

extern "C" void scalar_mult(float a, float b, float &prod) {
    // This function adds two integers and returns the result
    #pragma HLS INTERFACE s_axilite port=a bundle=CTRL
    #pragma HLS INTERFACE s_axilite port=b bundle=CTRL
    #pragma HLS INTERFACE s_axilite port=prod bundle=CTRL    
    #pragma HLS INTERFACE s_axilite port=return bundle=CTRL
    prod = a * b * 2;
}
