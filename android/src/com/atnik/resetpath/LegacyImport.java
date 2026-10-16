package com.atnik.resetpath;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;

/**
 * Reads the SQLite database left by ResetPath 0.1/0.2 (the Python build), so
 * an in-place upgrade keeps the user's tasks, diary pages, and reflections.
 * Returns "" when there is nothing to import.
 */
final class LegacyImport {
    private LegacyImport() {}

    static String read(Context context) {
        File database = find(new File(context.getApplicationInfo().dataDir), 0);
        if (database == null) return "";
        try (SQLiteDatabase db = SQLiteDatabase.openDatabase(database.getPath(), null, SQLiteDatabase.OPEN_READONLY)) {
            JSONObject out = new JSONObject();
            out.put("tasks", rows(db, "SELECT title, track, planned_date, completed_at, created_at FROM tasks"));
            out.put("diary", rows(db, "SELECT body, created_at, updated_at FROM diary_entries"));
            out.put("thoughts", rows(db, "SELECT thought, next_action, created_at FROM thought_entries"));
            out.put("settings", rows(db, "SELECT trusted_person_name, trusted_person_phone, theme_mode FROM settings"));
            return out.toString();
        } catch (Exception error) {
            return "";
        }
    }

    private static File find(File dir, int depth) {
        File[] files = dir.listFiles();
        if (files == null || depth > 6) return null;
        for (File file : files) {
            if (file.isFile() && file.getName().equals("resetpath.db")) return file;
        }
        for (File file : files) {
            if (file.isDirectory()) {
                File found = find(file, depth + 1);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static JSONArray rows(SQLiteDatabase db, String sql) throws JSONException {
        JSONArray array = new JSONArray();
        try (Cursor cursor = db.rawQuery(sql, null)) {
            while (cursor.moveToNext()) {
                JSONObject row = new JSONObject();
                for (int i = 0; i < cursor.getColumnCount(); i++) {
                    row.put(cursor.getColumnName(i), cursor.isNull(i) ? JSONObject.NULL : cursor.getString(i));
                }
                array.put(row);
            }
        } catch (RuntimeException missingTable) {
            // Older databases may not have every table.
        }
        return array;
    }
}
