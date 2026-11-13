package org.junit.jupiter.api;

import org.junit.jupiter.api.function.Executable;

/**
 * LOCAL VERIFICATION ONLY. Implements just the subset of JUnit 5 assertions that engine tests may use:
 * assertEquals(long,long), assertEquals(double,double,double), assertEquals(Object,Object), assertTrue,
 * assertFalse, assertNull, assertNotNull, assertThrows.
 */
public final class Assertions {
    private Assertions() { }

    public static void assertEquals(long expected, long actual) {
        if (expected != actual) throw new AssertionError("expected: <" + expected + "> but was: <" + actual + ">");
    }

    public static void assertEquals(double expected, double actual, double delta) {
        if (Double.compare(expected, actual) != 0 && !(Math.abs(expected - actual) <= delta)) {
            throw new AssertionError("expected: <" + expected + "> but was: <" + actual + "> (delta " + delta + ")");
        }
    }

    public static void assertEquals(Object expected, Object actual) {
        if (expected == null ? actual != null : !expected.equals(actual)) {
            throw new AssertionError("expected: <" + expected + "> but was: <" + actual + ">");
        }
    }

    public static void assertTrue(boolean condition) {
        if (!condition) throw new AssertionError("expected true");
    }

    public static void assertTrue(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void assertFalse(boolean condition) {
        if (condition) throw new AssertionError("expected false");
    }

    public static void assertFalse(boolean condition, String message) {
        if (condition) throw new AssertionError(message);
    }

    public static void assertNull(Object actual) {
        if (actual != null) throw new AssertionError("expected null but was: <" + actual + ">");
    }

    public static void assertNotNull(Object actual) {
        if (actual == null) throw new AssertionError("expected not null");
    }

    public static <T extends Throwable> T assertThrows(Class<T> expectedType, Executable executable) {
        try {
            executable.execute();
        } catch (Throwable t) {
            if (expectedType.isInstance(t)) return expectedType.cast(t);
            throw new AssertionError("expected " + expectedType.getName() + " but got " + t, t);
        }
        throw new AssertionError("expected " + expectedType.getName() + " to be thrown, but nothing was thrown");
    }
}
