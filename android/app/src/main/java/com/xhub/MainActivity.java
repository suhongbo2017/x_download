package com.xhub;

import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WebView webView = new WebView(this);
        setContentView(webView);
        
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("http://43.119.35.237:8866");
    }
    
    @Override
    public void onBackPressed() {
        WebView webView = (WebView) findViewById(android.R.id.content).getRootView().findViewWithTag("webview");
        // Simple back support
        super.onBackPressed();
    }
}
