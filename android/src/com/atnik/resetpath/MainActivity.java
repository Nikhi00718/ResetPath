package com.atnik.resetpath;

import android.Manifest;
import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * A thin shell around the offline web app in assets/web. Pages are served
 * from a virtual https origin so WebView storage behaves like a normal site,
 * and the app never touches the network.
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START_URL = "https://" + HOST + "/index.html";
    private static final int REQUEST_OPEN_FILE = 1;
    private static final int REQUEST_SAVE_FILE = 2;
    private static final int REQUEST_NOTIFICATIONS = 3;
    private static final String FOCUS_CHANNEL = "focus";

    private static final Map<String, String> MIME = new HashMap<>();

    static {
        MIME.put("html", "text/html");
        MIME.put("js", "text/javascript");
        MIME.put("css", "text/css");
        MIME.put("json", "application/json");
        MIME.put("png", "image/png");
        MIME.put("svg", "image/svg+xml");
        MIME.put("webmanifest", "application/manifest+json");
    }

    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private String pendingSave;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#0D1416"));
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        setContentView(web);

        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setTextZoom(100);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if (!HOST.equals(url.getHost())) {
                    // Block every network request; the app is fully offline.
                    return new WebResourceResponse("text/plain", "utf-8", 403, "Offline", null, null);
                }
                return serveAsset(url.getPath());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if (HOST.equals(url.getHost())) return false;
                String scheme = url.getScheme();
                try {
                    if ("tel".equals(scheme)) {
                        startActivity(new Intent(Intent.ACTION_DIAL, url));
                    } else if ("https".equals(scheme) || "mailto".equals(scheme)) {
                        startActivity(new Intent(Intent.ACTION_VIEW, url));
                    }
                } catch (ActivityNotFoundException ignored) {
                    toast("No app can open this link");
                }
                return true;
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                try {
                    startActivityForResult(intent, REQUEST_OPEN_FILE);
                } catch (ActivityNotFoundException error) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }
        });

        web.addJavascriptInterface(new Bridge(), "ResetPathNative");
        createChannels();
        if (savedInstanceState != null) web.restoreState(savedInstanceState);
        else web.loadUrl(START_URL);
    }

    private WebResourceResponse serveAsset(String path) {
        if (path == null || path.equals("/") || path.isEmpty()) path = "/index.html";
        if (path.contains("..")) return new WebResourceResponse("text/plain", "utf-8", 404, "Not found", null, null);
        String extension = path.substring(path.lastIndexOf('.') + 1);
        String mime = MIME.containsKey(extension) ? MIME.get(extension) : "application/octet-stream";
        try {
            InputStream stream = getAssets().open("web" + path);
            Map<String, String> headers = new HashMap<>();
            headers.put("Cache-Control", "no-cache");
            return new WebResourceResponse(mime, "utf-8", 200, "OK", headers, stream);
        } catch (IOException error) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not found", null, null);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript("window.rpBack ? window.rpBack() : false", value -> {
            if (!"true".equals(value)) moveTaskToBack(true);
        });
    }

    // The WebView is deliberately not paused in onPause, so ambient sound
    // keeps playing with the screen off. PlaybackService keeps the process
    // alive while sound is active.

    @Override
    protected void onDestroy() {
        stopService(new Intent(this, PlaybackService.class));
        web.destroy();
        super.onDestroy();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        Uri uri = resultCode == RESULT_OK && data != null ? data.getData() : null;
        if (requestCode == REQUEST_OPEN_FILE && fileCallback != null) {
            fileCallback.onReceiveValue(uri == null ? null : new Uri[] {uri});
            fileCallback = null;
        } else if (requestCode == REQUEST_SAVE_FILE) {
            String text = pendingSave;
            pendingSave = null;
            if (uri == null || text == null) return;
            try (OutputStream out = getContentResolver().openOutputStream(uri, "wt")) {
                out.write(text.getBytes(StandardCharsets.UTF_8));
                toast("Backup saved");
            } catch (IOException | NullPointerException error) {
                toast("Could not save the backup");
            }
        }
    }

    private void createChannels() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(
                new NotificationChannel(FOCUS_CHANNEL, "Focus timer", NotificationManager.IMPORTANCE_DEFAULT));
        manager.createNotificationChannel(
                new NotificationChannel(PlaybackService.CHANNEL, "Ambient sound", NotificationManager.IMPORTANCE_LOW));
    }

    private void askForNotifications() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {Manifest.permission.POST_NOTIFICATIONS}, REQUEST_NOTIFICATIONS);
        }
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    static PendingIntent openAppIntent(Context context) {
        Intent intent = new Intent(context, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_IMMUTABLE);
    }

    /** Methods callable from JavaScript as window.ResetPathNative.*. */
    private class Bridge {
        private boolean audioOn = false;
        private boolean askedForNotifications = false;

        @JavascriptInterface
        public void keepAwake(boolean on) {
            runOnUiThread(() -> {
                if (on) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            });
        }

        @JavascriptInterface
        public void audioActive(boolean on) {
            if (on == audioOn) return;
            audioOn = on;
            runOnUiThread(() -> {
                Intent intent = new Intent(MainActivity.this, PlaybackService.class);
                if (on) {
                    if (!askedForNotifications) {
                        askedForNotifications = true;
                        askForNotifications();
                    }
                    if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent);
                    else startService(intent);
                } else {
                    stopService(intent);
                }
            });
        }

        @JavascriptInterface
        public void notify(String title, String text) {
            runOnUiThread(() -> {
                NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
                Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                        ? new Notification.Builder(MainActivity.this, FOCUS_CHANNEL)
                        : new Notification.Builder(MainActivity.this);
                builder.setSmallIcon(R.mipmap.ic_launcher)
                        .setContentTitle(title)
                        .setContentText(text)
                        .setAutoCancel(true)
                        .setContentIntent(openAppIntent(MainActivity.this));
                try {
                    manager.notify(2, builder.build());
                } catch (SecurityException ignored) {
                    // Notifications are off; the in-app chime and vibration still ran.
                }
            });
        }

        @JavascriptInterface
        public void setBars(String color, boolean light) {
            runOnUiThread(() -> {
                int parsed = Color.parseColor(color);
                getWindow().setStatusBarColor(parsed);
                getWindow().setNavigationBarColor(parsed);
                web.setBackgroundColor(parsed);
                int flags = 0;
                if (light) {
                    flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
                    if (Build.VERSION.SDK_INT >= 26) flags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                }
                getWindow().getDecorView().setSystemUiVisibility(flags);
            });
        }

        @JavascriptInterface
        public void saveFile(String name, String mime, String text) {
            runOnUiThread(() -> {
                pendingSave = text;
                Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType(mime);
                intent.putExtra(Intent.EXTRA_TITLE, name);
                try {
                    startActivityForResult(intent, REQUEST_SAVE_FILE);
                } catch (ActivityNotFoundException error) {
                    pendingSave = null;
                    toast("No file app is available to save the backup");
                }
            });
        }

        @JavascriptInterface
        public String legacyData() {
            return LegacyImport.read(MainActivity.this);
        }
    }
}
