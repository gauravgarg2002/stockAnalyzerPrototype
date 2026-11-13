import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * LOCAL VERIFICATION ONLY. Runs every @Test method (no-arg) of the given classes by reflection, with a fresh
 * instance per method. Prints one line per test, then pass/fail counts. Exit code 1 if any test fails or
 * nothing ran.
 */
public final class EngineTestRunner {
    public static void main(String[] args) throws Exception {
        int pass = 0, fail = 0;
        List<String> failures = new ArrayList<>();
        for (String cn : args) {
            Class<?> c = Class.forName(cn);
            List<Method> methods = new ArrayList<>();
            for (Method m : c.getDeclaredMethods()) {
                if (m.isAnnotationPresent(Test.class)) methods.add(m);
            }
            methods.sort(Comparator.comparing(Method::getName));
            for (Method m : methods) {
                String id = c.getSimpleName() + "." + m.getName();
                try {
                    var ctor = c.getDeclaredConstructor();
                    ctor.setAccessible(true);
                    Object inst = ctor.newInstance();
                    m.setAccessible(true);
                    m.invoke(inst);
                    pass++;
                    System.out.println("PASS " + id);
                } catch (InvocationTargetException e) {
                    fail++;
                    Throwable t = e.getCause();
                    failures.add(id + ": " + t);
                    System.out.println("FAIL " + id + ": " + t);
                    StackTraceElement[] st = t.getStackTrace();
                    for (int i = 0; i < Math.min(4, st.length); i++) System.out.println("     at " + st[i]);
                } catch (Exception e) {
                    fail++;
                    failures.add(id + ": " + e);
                    System.out.println("FAIL " + id + ": " + e);
                }
            }
        }
        System.out.println();
        System.out.println("Tests run: " + (pass + fail) + ", passed: " + pass + ", failed: " + fail);
        if (!failures.isEmpty()) {
            System.out.println("Failures:");
            for (String f : failures) System.out.println("  " + f);
        }
        System.exit(fail > 0 || pass == 0 ? 1 : 0);
    }
}
