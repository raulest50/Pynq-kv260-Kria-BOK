// adder_hls.cpp
#include <iostream>

extern "C" int adder(int a, int b, int &sum) {
    // This function adds two integers and returns the result
    #pragma HLS INTERFACE s_axilite port=a bundle=CTRL
    #pragma HLS INTERFACE s_axilite port=b bundle=CTRL
    #pragma HLS INTERFACE s_axilite port=sum bundle=CTRL    
    #pragma HLS INTERFACE s_axilite port=return bundle=CTRL
    sum = a + b + 2;
    return sum;
}
