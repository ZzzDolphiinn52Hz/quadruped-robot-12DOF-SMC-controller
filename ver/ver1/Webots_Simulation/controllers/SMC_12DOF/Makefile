null :=
space := $(null) $(null)
WEBOTS_HOME_PATH?=$(subst $(space),\ ,$(strip $(subst \,/,$(WEBOTS_HOME))))

C_SOURCES = SMC_12DOF.c math_utils.c
CFLAGS = -Wno-unused-result
LIBRARIES = -lws2_32

include $(WEBOTS_HOME_PATH)/resources/Makefile.include
