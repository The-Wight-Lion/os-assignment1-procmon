CC      = gcc
CFLAGS  = -Wall -Wextra -O2 -std=c11
BIN     = bin

all: $(BIN)/procmon $(BIN)/workload

$(BIN)/procmon: src/procmon.c | $(BIN)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN)/workload: src/workload.c | $(BIN)
	$(CC) $(CFLAGS) -o $@ $<

$(BIN):
	mkdir -p $(BIN)

test: all
	bash tests/run_tests.sh

clean:
	rm -rf $(BIN)

.PHONY: all test clean
