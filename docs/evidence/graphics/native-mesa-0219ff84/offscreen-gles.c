#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <dlfcn.h>
typedef void* D; typedef void* S; typedef void* C; typedef void* Config; typedef int I; typedef unsigned int U; typedef unsigned char B; typedef char Ch; typedef float F;
#define NO ((void*)0)
#define NONE 0x3038
#define PLATFORM_SURFACELESS 0x31DD
#define SURFACE_TYPE 0x3033
#define PBUFFER_BIT 0x0001
#define RENDERABLE_TYPE 0x3040
#define ES3_BIT 0x0040
#define RED_SIZE 0x3024
#define GREEN_SIZE 0x3023
#define BLUE_SIZE 0x3022
#define WIDTH 0x3057
#define HEIGHT 0x3056
#define CLIENT_VERSION 0x3098
#define ES_API 0x30A0
#define VERTEX_SHADER 0x8B31
#define FRAGMENT_SHADER 0x8B30
#define COMPILE_STATUS 0x8B81
#define LINK_STATUS 0x8B82
#define TRIANGLES 0x0004
#define DITHER 0x0BD0
#define COLOR_BUFFER_BIT 0x00004000
#define EGL_NO_SURFACE ((S)0)
#define EGL_NO_CONTEXT ((C)0)
#define EGL_DEFAULT_DISPLAY ((void*)0)
static D (*getplat)(U,void*,const I*); static I(*init)(D,I*,I*); static I(*bindapi)(U); static I(*choose)(D,const I*,Config*,I,I*); static S(*pbuffer)(D,Config,const I*); static C(*context)(D,Config,C,const I*); static I(*current)(D,S,S,C); static Ch*(*query)(D,I); static I(*destroyc)(D,C); static I(*destroys)(D,S); static I(*term)(D); static I(*geterr)(void);
static U(*create_shader)(U); static void(*shader_src)(U,I,const Ch*const*,const I*); static void(*compile_shader)(U); static void(*get_shader)(U,U,I*); static void(*shader_log)(U,I,I*,Ch*); static U(*create_program)(void); static void(*attach)(U,U); static void(*link)(U); static void(*get_program)(U,U,I*); static void(*program_log)(U,I,I*,Ch*); static void(*use)(U); static void(*viewport)(I,I,I,I); static void(*disable)(U); static void(*draw)(U,I,I); static void(*finish)(void); static const B*(*getstr)(U);
static void *sym(void *h,const char*n){void*p=dlsym(h,n);if(!p){fprintf(stderr,"missing symbol %s\n",n);exit(2);}return p;}
static double now_s(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static U compile(U type,const Ch*src){U s=create_shader(type);shader_src(s,1,&src,NULL);compile_shader(s);I ok=0;get_shader(s,COMPILE_STATUS,&ok);if(!ok){Ch log[2048];shader_log(s,sizeof log,NULL,log);fprintf(stderr,"shader: %s\n",log);exit(2);}return s;}
int main(int argc,char**argv){int w=argc>1?atoi(argv[1]):1280,h=argc>2?atoi(argv[2]):720,secs=argc>3?atoi(argv[3]):10;void*eh=dlopen("libEGL.so",RTLD_NOW|RTLD_LOCAL),*gh=dlopen("libGLESv2.so",RTLD_NOW|RTLD_LOCAL);if(!eh||!gh){fprintf(stderr,"dlopen failed: %s\n",dlerror());return 2;}
getplat=(void*)sym(eh,"eglGetPlatformDisplay");init=(void*)sym(eh,"eglInitialize");bindapi=(void*)sym(eh,"eglBindAPI");choose=(void*)sym(eh,"eglChooseConfig");pbuffer=(void*)sym(eh,"eglCreatePbufferSurface");context=(void*)sym(eh,"eglCreateContext");current=(void*)sym(eh,"eglMakeCurrent");query=(void*)sym(eh,"eglQueryString");destroyc=(void*)sym(eh,"eglDestroyContext");destroys=(void*)sym(eh,"eglDestroySurface");term=(void*)sym(eh,"eglTerminate");geterr=(void*)sym(eh,"eglGetError");
create_shader=(void*)sym(gh,"glCreateShader");shader_src=(void*)sym(gh,"glShaderSource");compile_shader=(void*)sym(gh,"glCompileShader");get_shader=(void*)sym(gh,"glGetShaderiv");shader_log=(void*)sym(gh,"glGetShaderInfoLog");create_program=(void*)sym(gh,"glCreateProgram");attach=(void*)sym(gh,"glAttachShader");link=(void*)sym(gh,"glLinkProgram");get_program=(void*)sym(gh,"glGetProgramiv");program_log=(void*)sym(gh,"glGetProgramInfoLog");use=(void*)sym(gh,"glUseProgram");viewport=(void*)sym(gh,"glViewport");disable=(void*)sym(gh,"glDisable");draw=(void*)sym(gh,"glDrawArrays");finish=(void*)sym(gh,"glFinish");getstr=(void*)sym(gh,"glGetString");
 D d=getplat(PLATFORM_SURFACELESS,EGL_DEFAULT_DISPLAY,NULL);I ma=0,mi=0;if(!d||!init(d,&ma,&mi)){fprintf(stderr,"eglInitialize failed 0x%x\n",geterr());return 2;}bindapi(ES_API);I aa[]={SURFACE_TYPE,PBUFFER_BIT,RENDERABLE_TYPE,ES3_BIT,RED_SIZE,8,GREEN_SIZE,8,BLUE_SIZE,8,NONE};Config cfg;I n=0;if(!choose(d,aa,&cfg,1,&n)||n<1){fprintf(stderr,"eglChooseConfig failed 0x%x\n",geterr());return 2;}I pa[]={WIDTH,w,HEIGHT,h,NONE};S surf=pbuffer(d,cfg,pa);I ca[]={CLIENT_VERSION,3,NONE};C ctx=context(d,cfg,EGL_NO_CONTEXT,ca);if(!surf||!ctx||!current(d,surf,surf,ctx)){fprintf(stderr,"context/pbuffer failed 0x%x\n",geterr());return 2;}
 const Ch*vs="#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}";const Ch*fs="#version 300 es\nprecision highp float;out vec4 color;void main(){vec2 p=gl_FragCoord.xy;float v=0.17;for(int i=0;i<48;i++){v=fract(v*1.6180339+dot(p,vec2(0.000013,0.000017))+float(i)*0.00031);v=abs(v*2.0-1.0);}color=vec4(v,fract(v*1.7),fract(v*2.3),1.0);} ";U prog=create_program(),a=compile(VERTEX_SHADER,vs),b=compile(FRAGMENT_SHADER,fs);attach(prog,a);attach(prog,b);link(prog);I ok=0;get_program(prog,LINK_STATUS,&ok);if(!ok){Ch log[2048];program_log(prog,sizeof log,NULL,log);fprintf(stderr,"link: %s\n",log);return 2;}use(prog);viewport(0,0,w,h);disable(DITHER);fprintf(stderr,"EGL=%s | GLES=%s | renderer=%s | pbuffer=%dx%d | shader=48-iteration full-screen fragment | glFinish/frame\n",query(d,0x3054),getstr(0x1F02),getstr(0x1F01),w,h);
 for(int i=0;i<120;i++){draw(TRIANGLES,0,3);finish();}double t0=now_s(),t=t0;unsigned long frames=0;while(t-t0<secs){draw(TRIANGLES,0,3);finish();frames++;t=now_s();}printf("elapsed=%.3f seconds frames=%lu throughput=%.2f frames/sec\n",t-t0,frames,frames/(t-t0));current(d,NULL,NULL,NULL);destroyc(d,ctx);destroys(d,surf);term(d);return 0;}
