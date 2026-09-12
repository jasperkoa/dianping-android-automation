import android.app.UiAutomation;
import android.os.HandlerThread;
import android.os.Looper;
import android.graphics.Rect;
import android.view.accessibility.AccessibilityNodeInfo;
import org.xmlpull.v1.XmlSerializer;

/** Read-only hierarchy snapshot without waiting for a countdown to become idle. */
public final class UiDump {
    static String clean(Object o) {
        if (o == null) return "";
        return o.toString().replaceAll("[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F]", "");
    }
    static void emit(XmlSerializer out, AccessibilityNodeInfo n, int depth) throws Exception {
        if (n == null || depth > 80) return;
        out.startTag(null, "node");
        out.attribute(null, "text", clean(n.getText()));
        out.attribute(null, "content-desc", clean(n.getContentDescription()));
        out.attribute(null, "package", clean(n.getPackageName()));
        out.attribute(null, "resource-id", clean(n.getViewIdResourceName()));
        out.attribute(null, "class", clean(n.getClassName()));
        out.attribute(null, "enabled", String.valueOf(n.isEnabled()));
        out.attribute(null, "clickable", String.valueOf(n.isClickable()));
        out.attribute(null, "scrollable", String.valueOf(n.isScrollable()));
        out.attribute(null, "checked", String.valueOf(n.isChecked()));
        out.attribute(null, "selected", String.valueOf(n.isSelected()));
        Rect r = new Rect();
        n.getBoundsInScreen(r);
        if (!n.isVisibleToUser()) r.setEmpty();
        out.attribute(null, "bounds", "["+r.left+","+r.top+"]["+r.right+","+r.bottom+"]");
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo c = n.getChild(i);
            if (c != null) {
                emit(out, c, depth+1);
                c.recycle();
            }
        }
        out.endTag(null, "node");
    }
    public static void main(String[] args) {
        HandlerThread thread = new HandlerThread("DianpingUiRead");
        UiAutomation ui = null;
        int result = 0;
        try {
            thread.start();
            Class<?> conn = Class.forName("android.app.IUiAutomationConnection");
            Object connection = Class.forName("android.app.UiAutomationConnection").newInstance();
            ui = (UiAutomation) UiAutomation.class.getConstructor(Looper.class, conn)
                .newInstance(thread.getLooper(), connection);
            UiAutomation.class.getMethod("connect", int.class).invoke(ui, 1);
            AccessibilityNodeInfo root = null;
            for (int attempt = 0; attempt < 15 && root == null; attempt++) {
                Thread.sleep(100);
                root = ui.getRootInActiveWindow();
            }
            if (root == null) throw new IllegalStateException("No active root");
            XmlSerializer out = android.util.Xml.newSerializer();
            out.setOutput(System.out, "UTF-8");
            out.startDocument("UTF-8", true);
            out.startTag(null, "hierarchy");
            emit(out, root, 0);
            out.endTag(null, "hierarchy");
            out.endDocument();
            out.flush();
            root.recycle();
        } catch (Throwable e) {
            e.printStackTrace(System.err);
            result = 1;
        } finally {
            if (ui != null) {
                try { UiAutomation.class.getMethod("disconnect").invoke(ui); }
                catch (Throwable ignored) { }
            }
            thread.quit();
        }
        System.exit(result);
    }
}
