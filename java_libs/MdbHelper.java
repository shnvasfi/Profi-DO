import java.sql.*;
import java.io.*;
import java.util.*;

/**
 * MdbHelper - Python subprocess ile çağrılır.
 * Stdin'den JSON satırları okur, SQL çalıştırır, sonucu stdout'a yazar.
 * UCanAccess JDBC ile MDB'ye yazar — JPype/JNI kullanmaz, crash yapmaz.
 *
 * Kullanım: java -cp "jars" MdbHelper /path/to/file.mdb
 */
public class MdbHelper {

    static Connection conn;

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: MdbHelper <mdb_path>");
            System.exit(1);
        }
        String dbPath = args[0];
        Class.forName("net.ucanaccess.jdbc.UcanaccessDriver");
        conn = DriverManager.getConnection(
            "jdbc:ucanaccess://" + dbPath + ";newDatabaseVersion=V2010", "", "");
        conn.setAutoCommit(false);

        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));
        PrintStream out = new PrintStream(System.out, true, "UTF-8");
        String line;

        while ((line = reader.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) continue;

            if (line.equals("COMMIT")) {
                try { conn.commit(); out.println("OK:COMMIT"); }
                catch (Exception e) { out.println("ERR:" + e.getMessage()); }
                continue;
            }

            if (line.startsWith("SELECT COUNT")) {
                try {
                    ResultSet rs = conn.createStatement().executeQuery(line);
                    rs.next();
                    out.println("COUNT:" + rs.getInt(1));
                } catch (Exception e) { out.println("ERR:" + e.getMessage()); }
                continue;
            }

            if (line.startsWith("SELECT ")) {
                try {
                    ResultSet rs = conn.createStatement().executeQuery(line);
                    ResultSetMetaData meta = rs.getMetaData();
                    int cols = meta.getColumnCount();
                    // Sütun adları
                    StringBuilder sb = new StringBuilder("COLS:");
                    for (int i = 1; i <= cols; i++) {
                        sb.append(meta.getColumnName(i));
                        if (i < cols) sb.append("\t");
                    }
                    out.println(sb);
                    // Satırlar
                    while (rs.next()) {
                        StringBuilder row = new StringBuilder("ROW:");
                        for (int i = 1; i <= cols; i++) {
                            String val = rs.getString(i);
                            row.append(val == null ? "\\N" : val.replace("\t", "\\t").replace("\n","\\n"));
                            if (i < cols) row.append("\t");
                        }
                        out.println(row);
                    }
                    out.println("END");
                } catch (Exception e) { out.println("ERR:" + e.getMessage()); }
                continue;
            }

            // INSERT / UPDATE / DELETE / CREATE / DROP
            try {
                conn.createStatement().execute(line);
                out.println("OK");
            } catch (Exception e) {
                out.println("ERR:" + e.getMessage().replace("\n", " "));
            }
        }
        conn.commit();
        conn.close();
    }
}
