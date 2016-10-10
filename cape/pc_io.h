#ifndef _PC_IO_H
#define _PC_IO_H

#include <byteswap.h>

// Byteswap macros
#define bs32(x) (*(unsigned *)&(x) = __bswap_32(*(unsigned *)&(x)))
#define bs64(x) (*(unsigned long *)&(x) = __bswap_64(*(unsigned long *)&(x)))

// Check if little-endian
int is_le(void);

// Get total size of NumPy array
int np_size(PyArrayObject *P);

// Byteswap functions for floats/doubles
float  swap_single(const float f);
double swap_double(const double f);      

// Individual integers
int pc_Write_b4_i(FILE *fid, int v);
int pc_Write_lb4_i(FILE *fid, int v);

// Big-endian single-precision writers
int pc_WriteRecord_b4_f1(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_b4_f2(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_b4_f3(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_b4_i1(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_b4_i2(FILE *fid, PyArrayObject *P);
// Big-endian double-precision writers
int pc_WriteRecord_b8_f1(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_b8_f2(FILE *fid, PyArrayObject *P);

// Little-endian single-precision writers
int pc_WriteRecord_lb4_f1(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_lb4_f2(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_lb4_f3(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_lb4_i1(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_lb4_i2(FILE *fid, PyArrayObject *P);
// Little-endian double-precision writers
int pc_WriteRecord_lb8_f1(FILE *fid, PyArrayObject *P);
int pc_WriteRecord_lb8_f2(FILE *fid, PyArrayObject *P);



# endif
                                      