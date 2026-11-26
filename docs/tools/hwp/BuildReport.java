import kr.dogfoot.hwplib.object.HWPFile;
import kr.dogfoot.hwplib.object.bindata.EmbeddedBinaryData;
import kr.dogfoot.hwplib.object.bodytext.ParagraphListInterface;
import kr.dogfoot.hwplib.object.bodytext.Section;
import kr.dogfoot.hwplib.object.bodytext.control.Control;
import kr.dogfoot.hwplib.object.bodytext.control.ControlTable;
import kr.dogfoot.hwplib.object.bodytext.control.gso.ControlPicture;
import kr.dogfoot.hwplib.object.bodytext.control.gso.ControlRectangle;
import kr.dogfoot.hwplib.object.bodytext.control.table.Cell;
import kr.dogfoot.hwplib.object.bodytext.control.table.Row;
import kr.dogfoot.hwplib.object.bodytext.paragraph.Paragraph;
import kr.dogfoot.hwplib.object.docinfo.BinData;
import kr.dogfoot.hwplib.reader.HWPReader;
import kr.dogfoot.hwplib.writer.HWPWriter;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Builds the Cellect A mid-progress report (hwp) on top of the MANUX 결과보고서 (1팀, 11/13),
 * the course-form report the team already submitted once. Its cover, heading styles, table styles,
 * Gantt chart and page setup are kept; every text, table row and picture is replaced with 2A content.
 * The demo-video appendix (section 3) is dropped. Paragraph numbers (S0[n]) refer to the template.
 * Content source: docs/report/midterm_v0.1.md.
 *
 * Usage: java -cp "<classes>;hwplib-1.1.11.jar" BuildReport MANUX_report.hwp out.hwp <figure dir> <wordmark.png>
 */
public class BuildReport {
    static HWPFile f;
    static Section s0, s1, s2;
    static Paragraph[] S0, S1, S2;
    static File figs;
    static Paragraph textProto;          // a plain value-cell paragraph, cloned for boxed text
    static final Set<Long> usedBins = new HashSet<>();

    // ---------- helpers (as in BuildPlan) ----------

    static void set(Paragraph p, String text) throws Exception {
        long cs = p.getCharShape().getPositonShapeIdPairList().get(0).getShapeId();
        p.deleteText();
        if (!text.isEmpty()) {
            p.createText();
            p.getText().addString(text);
        }
        p.deleteCharShape();
        p.createCharShape();
        p.getCharShape().addParaCharShape(0, cs);
        p.deleteLineSeg();
        p.deleteRangeTag();
        p.getHeader().setCharacterCount(text.length() + 1);
        p.getHeader().setCharShapeCount(1);
        p.getHeader().setLineAlignCount(0);
        p.getHeader().setRangeTagCount(0);
    }

    /** Fill a list (cell or text box) with one paragraph per line, cloning its first paragraph. */
    static void lines(ParagraphListInterface pl, String value) throws Exception {
        String[] ls = value.split("\n", -1);
        Paragraph proto = pl.getParagraph(0);
        for (int i = 0; i < ls.length; i++) {
            if (i >= pl.getParagraphCount()) pl.insertParagraph(pl.getParagraphCount(), proto.clone());
            set(pl.getParagraph(i), ls[i]);
        }
        while (pl.getParagraphCount() > ls.length) pl.deleteParagraph(pl.getParagraphCount() - 1);
        for (int i = 0; i < pl.getParagraphCount(); i++) pl.getParagraph(i).getHeader().setLastInList(i == ls.length - 1);
    }

    static void cell(Cell c, String value) throws Exception {
        lines(c.getParagraphList(), value);
        c.getListHeader().setParaCount(c.getParagraphList().getParagraphCount());
    }

    static ControlTable table(Paragraph p) {
        for (Control c : p.getControlList()) if (c instanceof ControlTable) return (ControlTable) c;
        throw new RuntimeException("no table in paragraph");
    }

    /** Rewrite a whole table. Rows beyond the content are removed; each row must match the template's cell count. */
    static void fill(Paragraph p, String[][] rows) throws Exception {
        ControlTable t = table(p);
        if (rows.length > t.getRowList().size()) throw new RuntimeException("template table has only " + t.getRowList().size() + " rows");
        long removed = 0;
        while (t.getRowList().size() > rows.length) {
            Row r = t.getRowList().remove(t.getRowList().size() - 1);
            removed += r.getCellList().get(0).getListHeader().getHeight();
            List<Integer> cc = t.getTable().getCellCountOfRowList();
            cc.remove(cc.size() - 1);
        }
        t.getTable().setRowCount(rows.length);
        t.getHeader().setHeight(t.getHeader().getHeight() - removed);
        for (int r = 0; r < rows.length; r++) {
            List<Cell> cells = t.getRowList().get(r).getCellList();
            if (cells.size() != rows[r].length) throw new RuntimeException("row " + r + ": " + cells.size() + " cells, content has " + rows[r].length);
            for (int k = 0; k < cells.size(); k++) if (rows[r][k] != null) cell(cells.get(k), rows[r][k]);
        }
    }

    /** A one-cell figure table becomes a text box: its picture paragraph is replaced by plain lines. */
    static void box(Paragraph p, String text, long lineHeight) throws Exception {
        ControlTable t = table(p);
        Cell c = t.getRowList().get(0).getCellList().get(0);
        ParagraphListInterface pl = c.getParagraphList();
        while (pl.getParagraphCount() > 0) pl.deleteParagraph(0);
        pl.insertParagraph(0, textProto.clone());
        cell(c, text);
        long h = text.split("\n").length * lineHeight + 1400;
        long old = c.getListHeader().getHeight();
        c.getListHeader().setHeight(h);
        t.getHeader().setHeight(t.getHeader().getHeight() - old + h);
    }

    static String binName(long id, String ext) { return String.format("BIN%04X.%s", id, ext); }

    static EmbeddedBinaryData embedded(long id) {
        for (EmbeddedBinaryData e : f.getBinData().getEmbeddedBinaryDataList())
            if (e.getName().toUpperCase().startsWith(binName(id, "").toUpperCase())) return e;
        throw new RuntimeException("no embedded data for bin " + id);
    }

    static void putPng(long id, byte[] png) {
        for (BinData b : f.getDocInfo().getBinDataList()) if (b.getBinDataID() == id) b.setExtensionForEmbedding("png");
        EmbeddedBinaryData e = embedded(id);
        e.setName(binName(id, "png"));
        e.setData(png);
    }

    static ControlPicture pictureIn(Paragraph para) {
        if (para.getControlList() != null)
            for (Control c : para.getControlList()) if (c instanceof ControlPicture) return (ControlPicture) c;
        throw new RuntimeException("no picture in paragraph");
    }

    /** The picture paragraph inside a figure table's cell. */
    static Paragraph pictureParaInCell(Cell c) {
        for (Paragraph p : c.getParagraphList())
            if (p.getControlList() != null) for (Control k : p.getControlList()) if (k instanceof ControlPicture) return p;
        throw new RuntimeException("no picture in cell");
    }

    /** Swap a picture for a PNG at the given width (height from the image ratio). */
    static void picture(Paragraph para, File src, long width) throws Exception {
        ControlPicture pic = pictureIn(para);
        BufferedImage img = ImageIO.read(src);
        long height = Math.round(width * (double) img.getHeight() / img.getWidth());
        long id = pic.getShapeComponentPicture().getPictureInfo().getBinItemID();
        putPng(id, Files.readAllBytes(src.toPath()));
        usedBins.add(id);
        pic.getHeader().setWidth(width);
        pic.getHeader().setHeight(height);
        var sc = pic.getShapeComponent();
        sc.setWidthAtCreate((int) width);
        sc.setHeightAtCreate((int) height);
        sc.setWidthAtCurrent((int) width);
        sc.setHeightAtCurrent((int) height);
        sc.setRotateXCenter((int) (width / 2));
        sc.setRotateYCenter((int) (height / 2));
        var p = pic.getShapeComponentPicture();
        p.getLeftTop().setX(0); p.getLeftTop().setY(0);
        p.getRightTop().setX(width); p.getRightTop().setY(0);
        p.getLeftBottom().setX(0); p.getLeftBottom().setY(height);
        p.getRightBottom().setX(width); p.getRightBottom().setY(height);
        p.setLeftAfterCutting(0); p.setTopAfterCutting(0);
        p.setRightAfterCutting((int) width); p.setBottomAfterCutting((int) height);
        p.setImageWidth(width);
        p.setImageHeight(height);
    }

    /** Figure table: picture in its cell, cell and table resized to the new picture height. */
    static void figure(Paragraph p, String file, long width) throws Exception {
        ControlTable t = table(p);
        Cell c = t.getRowList().get(0).getCellList().get(0);
        Paragraph pp = pictureParaInCell(c);
        picture(pp, new File(figs, file), width);
        long h = pictureIn(pp).getHeader().getHeight() + 1200;
        long old = c.getListHeader().getHeight();
        c.getListHeader().setHeight(h);
        t.getHeader().setHeight(t.getHeader().getHeight() - old + h);
    }

    static int indexOf(Section s, Paragraph p) {
        for (int i = 0; i < s.getParagraphCount(); i++) if (s.getParagraph(i) == p) return i;
        throw new RuntimeException("paragraph not found");
    }

    static void delete(Section s, Paragraph[] P, int... idx) {
        for (int i : idx) s.deleteParagraph(indexOf(s, P[i]));
    }

    static void deleteRange(Section s, Paragraph[] P, int from, int to) {
        for (int i = from; i <= to; i++) delete(s, P, i);
    }

    /** Every embedded image no remaining picture points at becomes a 1x1 white PNG (no template images left in the file). */
    static void blankUnusedBins() throws Exception {
        Set<Long> live = new HashSet<>(usedBins);
        for (Section s : f.getBodyText().getSectionList()) for (Paragraph p : s) collectBins(p, live);
        BufferedImage dot = new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB);
        dot.setRGB(0, 0, 0xFFFFFF);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ImageIO.write(dot, "png", out);
        for (BinData b : f.getDocInfo().getBinDataList())
            if (!live.contains((long) b.getBinDataID())) {
                try { putPng(b.getBinDataID(), out.toByteArray()); } catch (RuntimeException ignored) { }
            }
    }

    static void collectBins(Paragraph p, Set<Long> live) {
        if (p.getControlList() == null) return;
        for (Control c : p.getControlList()) {
            if (c instanceof ControlPicture) live.add((long) ((ControlPicture) c).getShapeComponentPicture().getPictureInfo().getBinItemID());
            if (c instanceof ControlTable)
                for (Row r : ((ControlTable) c).getRowList()) for (Cell cell : r.getCellList()) for (Paragraph cp : cell.getParagraphList()) collectBins(cp, live);
            if (c instanceof ControlRectangle && ((ControlRectangle) c).getTextBox() != null)
                for (Paragraph cp : ((ControlRectangle) c).getTextBox().getParagraphList()) collectBins(cp, live);
        }
    }

    // ---------- Gantt (section 1) ----------

    // Fill ids in the template: empty week-start / normal / week-end, and the bar version of each.
    static final Map<Integer, Integer> BAR_TO_EMPTY = Map.of(53, 49, 51, 50, 52, 54, 60, 56, 58, 57, 59, 61);
    static final Map<Integer, Integer> EMPTY_TO_BAR = Map.of(49, 53, 50, 51, 54, 52, 56, 60, 57, 58, 61, 59);

    /** Time cells of a Gantt row: the 40 cells after the phase/task label cells (phase rows end with a status cell). */
    static List<Cell> timeCells(Row r) {
        List<Cell> cs = r.getCellList();
        int start = cs.size() == 43 ? 2 : 1;
        return new ArrayList<>(cs.subList(start, start + 40));
    }

    /** Clear a row's bars, then draw one bar over the buckets [from, to] (8 buckets x 5 cells). */
    static void bar(Row r, int from, int to) {
        List<Cell> tc = timeCells(r);
        for (int i = 0; i < tc.size(); i++) {
            var lh = tc.get(i).getListHeader();
            int bf = lh.getBorderFillId();
            if (!BAR_TO_EMPTY.containsKey(bf) && !EMPTY_TO_BAR.containsKey(bf)) continue;   // row-edge cell, no bar version
            int empty = BAR_TO_EMPTY.getOrDefault(bf, bf);
            boolean on = i >= from * 5 && i < (to + 1) * 5;
            lh.setBorderFillId(on ? EMPTY_TO_BAR.get(empty) : empty);
        }
    }

    // ---------- content ----------

    static final String GAP = "[확인 필요]";

    public static void main(String[] a) throws Exception {
        f = HWPReader.fromFile(a[0]);
        figs = new File(a[2]);
        File wordmark = new File(a[3]);
        s0 = f.getBodyText().getSectionList().get(0);
        s1 = f.getBodyText().getSectionList().get(1);
        s2 = f.getBodyText().getSectionList().get(2);
        S0 = s0.getParagraphs().clone();
        S1 = s1.getParagraphs().clone();
        S2 = s2.getParagraphs().clone();
        textProto = table(S0[42]).getRowList().get(0).getCellList().get(1).getParagraphList().getParagraph(0).clone();

        // ===== Cover =====
        lines(table(S0[0]).getRowList().get(0).getCellList().get(0).getParagraphList(),
            "  「[인텔] AI융합 DX마스터 클래스 7기」\n디지털 트윈 프로젝트 중간보고서");
        Cell coverCell = table(S0[1]).getRowList().get(0).getCellList().get(0);
        // the cover cell has the project-name line, and a separate paragraph holding the info table and picture
        Paragraph namePara = null, coverPara = null;
        for (Paragraph p : coverCell.getParagraphList()) {
            if (p.getNormalString().contains("프로젝트명")) namePara = p;
            if (p.getControlList() != null) for (Control c : p.getControlList()) if (c instanceof ControlTable) coverPara = p;
        }
        if (namePara.getControlList() == null) set(namePara, "【 프로젝트명 : Project Cellect A 】");
        else replaceLeadingText(namePara, "【 프로젝트명 : Project Cellect A 】");
        fill(coverPara, new String[][]{
            {"교과목명", "공정설비 디지털트윈 모델링"},
            {"지도교수", "김 유 성"},
            {"기    간", "2026. 11. 17 ~ (진행 중)"},
            {"발표일시", "2026년 12월 2일"},
            {"팀  구분", "Cellect (2A)"},
            {"팀    장", "최예현"},
            {"팀    원", "이순필, 박해준, 정연우, 김동혁"}});
        picture(pictureParaInCell(coverCell), wordmark, 22000);
        lines(table(S0[2]).getRowList().get(0).getCellList().get(0).getParagraphList(), "『Project Cellect A』 프로젝트 중간 보고");

        // ===== 1. 프로젝트 개요 =====
        ControlRectangle goals = null, pick = null;
        for (Control c : S0[5].getControlList()) if (c instanceof ControlRectangle) goals = (ControlRectangle) c;
        for (Control c : S0[7].getControlList()) if (c instanceof ControlRectangle) pick = (ControlRectangle) c;
        lines(goals.getTextBox().getParagraphList(),
            "Factory I/O 가상 전공정을 MELSEC Q 래더로 제어\n"
            + "입고·검사·분류·4셀 공급 시퀀스와 셀 위치별 추적\n"
            + "Factory I/O·PLC·SCADA 태그 연동, 후공정(2B) 인터록\n"
            + "셀마다 검사값·판정·박스 구성을 공용 DB에 기록\n"
            + "같은 전압 구간 4셀 세트로 세트 안 편차 감소\n"
            + "NG·보류 LOT 셀의 공급 유출 차단\n"
            + "셀 단위 데이터로 수율·장비 편향을 숫자로 확인");
        goals.getTextBox().getListHeader().setParaCount(goals.getTextBox().getParagraphList().getParagraphCount());
        lines(pick.getTextBox().getParagraphList(), "『Project Cellect A』 프로젝트 선정!");

        set(S0[10], "세트 안 셀 전압 편차");
        set(S0[11], "들어온 순서대로 4개씩 묶으면 세트 안 셀 전압 편차가 커짐");
        set(S0[12], "전압 구간(A·B·C)별로 모았다가 같은 구간 4개씩 공급하면 편차를 줄일 수 있음");
        set(S0[13], "확인 기준(잠정): 순서대로 묶은 세트 대비 세트 안 전압 편차 50% 이상 감소");
        set(S0[16], "불량 셀과 LOT 불량의 유출");
        set(S0[17], "불량 셀이 조립 설비로 넘어가거나 한 LOT에서 불량이 반복돼도 계속 공급될 위험이 있어, 셀마다 판정해 NG는 격리하고 LOT별 NG 누계가 3건이면 그 LOT 공급을 보류");
        set(S0[19], "공정 사이 이력 단절 – Cellect의 출발점");
        set(S0[20], "셀·세트 이력이 공정 사이에서 끊기면 불량 원인을 되짚기 어려움");
        set(S0[21], "셀 ID·세트 ID를 공용 DB에 기록하고 후공정(2B)으로 넘겨, 팩 → 셀 → 검사값까지 추적할 수 있게 함");

        fill(S0[24], new String[][]{
            {"구 분", "이 름", "주요 임무", "비고"},
            {"1", "최예현", "프로젝트·일정 관리\n공용 DB·API·수집기", "팀장"},
            {"2", "정연우", "SCADA · HMI · DB\n" + GAP + " 담당 범위", ""},
            {"3", "이순필", "PLC · Factory I/O\n" + GAP + " 담당 범위", ""},
            {"4", "박해준", "PLC · Factory I/O\n" + GAP + " 담당 범위", ""},
            {"5", "김동혁", "PLC · Factory I/O\n" + GAP + " 담당 범위", ""},
            {"6", "전원", "중간보고서·발표 자료 작성", "공동"},
            {"7", "전원", "통합 시험\nGitHub 협업 관리", "공동"}});

        // ===== 2. 시스템 구조 및 사양 =====
        figure(S0[28], "system.png", 46000);
        fill(S0[34], new String[][]{
            {"구 분", "사양 및 규격", "수량", "비고"},
            {"P  L  C", "Mitsubishi MELSEC Q03UDE · GX Works2", "1", "제어"},
            {"시뮬레이터", "Factory I/O v2.5 Modbus & OPC Edition", "1", "가상 공정"},
            {"PLC 시뮬레이션", "GX Simulator2", "1식", "래더 실행"},
            {"통    신", "Modbus TCP · MX Component", "1식", "브리지"},
            {"시연용 PLC", "Python 소프트 PLC", "1식", "시연·개발"},
            {"언    어", "Python 3.12 이상", "1식", "브리지·수집기"},
            {"협    업", "GitHub (digital-twin-a · battery-db)", "1식", "관리"},
            {"DB 서버", "Oracle Cloud VM (E2.1.Micro, 1 GB)", "1", "데이터 / 관제"},
            {"D     B", "PostgreSQL 16 (테이블 22 · 뷰 10)", "1식"},
            {"A P I", "FastAPI · Caddy (HTTPS) · API 키", "1식"},
            {"수 집 기", "Python · SQLite 로컬 저장", "1식"},
            {"S C A D A", "Grafana OSS 13.3.1", "1식"},
            {"H  M  I", "2A HMI v0.2 설계 · 오프라인 시제품", "1식"},
            {"접    속", "SSH 터널 · Tailscale", "1식"}});

        set(S0[36], "Factory I/O v2 씬 (11/23 저장본)");
        Cell sceneCell = table(S0[37]).getRowList().get(0).getCellList().get(0);
        picture(pictureParaInCell(sceneCell), new File(figs, "scene.png"), 16000);
        fill(S0[37], new String[][]{
            {null, "저    장", "2026. 11. 23 09:32 (iiio.factoryio)"},
            {"검 사 기", "Machining Center 5 (검사 4 + 재검 1)"},
            {"적    재", "Pick & Place 3 (레인별 박스)"},
            {"반    송", "벨트·롤러 컨베이어 49, 턴테이블 3"},
            {"분    기", "푸셔 7, 롤러 스톱 5"},
            {"검    출", "비전 2 · 위치 센서 0"},
            {"태    그", "Modbus 연결 0 → 센서·태그 연결 전"}});

        set(S0[40], "공용 DB 서버 (battery-db)");
        fill(S0[42], new String[][]{
            {"V      M", "Oracle Cloud E2.1.Micro (1 GB + 스왑 2 GB), Ubuntu 24.04"},
            {"D      B", "PostgreSQL 16, 테이블 22 · 뷰 10"},
            {"접    속", "DB 포트 비공개, SSH 터널 · Tailscale 예비"},
            {"계    정", "라인별 쓰기 계정 분리, 읽기·Grafana 전용 계정"},
            {"A  P  I", "FastAPI · HTTPS · API 키, 키별 사용 기록"},
            {"백    업", "6시간마다, VM 14일 · 관리자 PC 60일 보관"},
            {"복원 시험", "11/26 통과 (테이블 22개 행 수 일치)"},
            {"성    능", "서버 내부 INSERT 초당 약 2,800건"}});
        set(S0[43], "PLC 이벤트 수집기");
        fill(S0[45], new String[][]{
            {"입    력", "PLC 메일박스 D2700~D2799 (제안), 100 ms 폴링"},
            {"저    장", "로컬 SQLite에 먼저 저장한 뒤 PLC에 ACK"},
            {"전    송", "1초마다 최대 500건, 실패하면 다시 보냄"},
            {"중    복", "(회차, 순번)으로 DB에 한 번만 저장"},
            {"감    시", "30초마다 상태 보고 (넘침·누락·밀린 전송)"},
            {"상    태", "개발·시험 완료, 미배포 (PR 검토 중)"}});

        // ===== 3. 프로젝트 결과 (section 0 tail) =====
        set(S0[47], "공정 설계");
        set(S0[48], "공정 v2 흐름 (11/23 미팅)");
        figure(S0[49], "process.png", 46000);

        // template-only parts of section 0: tech-stack picture, MediaPipe/UI/MLP/TCN pictures, product screens
        delete(s0, S0, 14, 18, 22, 30, 31, 38, 39, 41, 44, 50, 51);

        // ===== 4. 프로젝트 일정 (section 1 Gantt) =====
        ControlTable g = table(S1[1]);
        List<Row> R = g.getRowList();
        List<Cell> months = R.get(0).getCellList();
        cell(months.get(3), "11月");
        cell(months.get(4), "11月");
        cell(months.get(5), "11月 ~ 12月");
        String[] weeks = {"11/17~", "11/19~", "11/21~", "11/23~", "11/25~", "11/27~", "11/29~", "12/1~"};
        for (int k = 0; k < 8; k++) cell(R.get(1).getCellList().get(3 + k), weeks[k]);
        // phase rows 4, 8, 12: [phase, task, ..., status]; task rows: [task, ...]
        String[][] tasks = {
            {"주제 선정 및\n역할 분담", "실시 계획서 작성\n(v0.14 ~ v0.18)", "공정 v2 재설계\n(11/23 미팅)"},
            {"Factory I/O 씬\nv2 배치·센서·태그", "PLC 래더\n(GX Works2)", "DB·API·수집기,\nSCADA·HMI 설계"},
            {"통합 시험\n(전체 연결)", "비정상 상황\n8건 시험", "중간보고서 작성 및\n발표 자료 제작, 발표"}};
        int[][][] bars = {
            {{0, 0}, {0, 0}, {3, 3}},
            {{1, 6}, {1, 6}, {2, 5}},
            {{5, 6}, {6, 6}, {4, 7}}};
        String[] status = {"종\n\n\n\n료", "진\n\n\n\n행", "예\n\n\n\n정"};
        for (int ph = 0; ph < 3; ph++) {
            int base = 4 + ph * 4;
            List<Cell> first = R.get(base).getCellList();
            cell(first.get(1), tasks[ph][0]);
            cell(first.get(first.size() - 1), status[ph]);
            bar(R.get(base), bars[ph][0][0], bars[ph][0][1]);
            for (int t = 1; t < 3; t++) {
                Row row = R.get(base + t);
                cell(row.getCellList().get(0), tasks[ph][t]);
                bar(row, bars[ph][t][0], bars[ph][t][1]);
            }
        }

        // ===== section 2: results, open issues, review =====
        long LH = 1700;
        set(S2[0], "공정 설계와 Factory I/O · PLC");
        set(S2[1], "v1 (계획서 v0.18) → v2 (11/23)");
        box(S2[2],
            "검사: 검사 위치 1곳 → 검사기 4대 병렬 (로봇 + Machining Center)\n"
            + "재검: 없음 → 재검 스테이션 (재검 1회 제안)\n"
            + "비전: 입고 1곳 (LOT) → 1차 ID · 2차 외관, 분류 전 ID 재확인\n"
            + "출구: 4셀 세트 배출 → 레인별 Pick & Place로 박스 적재 → 2B 인계\n"
            + "검토에서 찾은 위험 3건: 최종 NG 출구 없음 · 피더 끝 Remover로 양품 유실 가능 · 병렬 검사 합류 후 순서 깨짐 " + GAP + " 반영 여부", LH);
        set(S2[3], "Factory I/O · PLC 진행 (저장소 기준)");
        box(S2[4],
            "line_v0 시연 씬 + 소프트 PLC: 입고 → 검사 → NG/A/B/C 분류 시연 가능, 4셀 공급은 추가 검증 필요\n"
            + "래더 (line_v0): 명령어 목록 CSV 생성, GX Works2 가져오기·컴파일은 미검증\n"
            + "PLC 디바이스: 2000~2999 대역 확정 (로봇 0~1999, 2B 3000~3999)\n"
            + "v2 팀 씬 (11/23 저장본): 배치 완료, 위치 센서 0 · Modbus 태그 0\n"
            + "GX Works2 래더 Z1~Z5, 셀 전압 실측: " + GAP, LH);
        set(S2[5], "시험 씬 prj01에서 확인한 것 (11/19)");
        box(S2[6],
            "벨트 속도 0.60 m/s, 셀 길이 약 0.38 m (센서 기록으로 측정)\n"
            + "푸셔: 센서 → 푸셔 거리 + 셀 절반만큼 기다렸다 밀고, 미는 동안 이어진 벨트를 세워야 셀이 안 틀어짐\n"
            + "Machining Center: 입구에 셀이 있을 때 Start 펄스, 투입 → 가공 시작 약 16초\n"
            + "90° 옆 벨트로 옮겨 탄 셀은 틀어져 기계 입구에 안 맞음 → Wheel Aligner 필요", LH);

        set(S2[13], "데이터 수집 · 공용 DB");
        set(S2[14], "수집 방식");
        box(S2[15],
            "셀이 지날 때마다가 아니라 값이 생기고 · 판정이 갈리고 · 소속이 바뀌는 곳만 기록 (셀 하나 9건 안팎)\n"
            + "PLC 메일박스 → 로컬 저장 → PLC에 ACK → 1초마다 묶어서 API 전송 → (회차, 순번)으로 중복 제거\n"
            + "메일박스 배치는 설정 파일로 분리: PLC 담당과 합의되면 설정만 바꿈\n"
            + "DB 스키마는 공정 v2 반영 (시연 회차, 1차·재검, 설비 상태 구간, 알람), 셀 ID R<회차>-<PLC 번호>", LH);
        set(S2[16], "시험 결과 (11/26, 시험용 DB, 끝나고 삭제)");
        box(S2[17],
            "가짜 PLC 120셀/분, 90초: 이벤트 1,178건 → DB 1,178행, 순번 빠짐 없음\n"
            + "같은 1,178건 재전송: 새로 들어간 행 0 (중복 제거)\n"
            + "수집 중 20초 인터넷 끊김: 로컬에 쌓였다가 복구 후 전부 전송, 잃은 이벤트 0\n"
            + "이벤트 3건 삭제 후 재전송: 빠진 구간 감지 → 3건 복구\n"
            + "자동 시험: 수집기 34개 · API 41개 통과 / 백업 복원: 테이블 22개 행 수 일치\n"
            + "오사카 서버 왕복 약 43 ms → 1건씩 보내면 초당 약 22건, 묶으면 1만 행 0.7초 미만", LH);

        set(S2[23], "SCADA · HMI");
        set(S2[24], "Grafana SCADA (읽기 전용)");
        box(S2[25],
            "업무별 대시보드 5종 + 발표용: 메인·회차 총괄, 공정 관제, 생산·인계, 품질·설비 분석, DB 이력·추적\n"
            + "공정 평면도에 T1~T4 병렬 검사, RT 재검, NG 배출, A/B/C 레인과 4셀 트레이 표시\n"
            + "공용 DB 읽기 검증 (11/24): 대시보드 SQL 10개 성공 (화면 개발용 가짜 데이터)\n"
            + "[그림 필요: Grafana 화면]", LH);
        set(S2[26], "2A HMI v0.2 (설계)");
        box(S2[27],
            "메인 운전, 검사·분류, 설정·알람 3개 화면과 데이터·명령 계약, PLC 태그 매핑\n"
            + "PLC에 쓰는 프로그램은 브리지 하나: HMI는 브리지에 조작을 요청\n"
            + "오프라인 시제품까지, PLC 연결·조작은 아직 없음\n"
            + "[그림 필요: HMI 와이어프레임]", LH);

        // MANUX-only results in section 2 (pictures and demo references)
        delete(s2, S2, 7, 8, 9, 10, 11, 12);
        deleteRange(s2, S2, 18, 22);
        deleteRange(s2, S2, 28, 42);

        set(S2[45], "미비점 식별 및 검토 결과");
        set(S2[46], "실제 데이터 연결 전 단계");
        set(S2[47], "PLC 이벤트 메일박스(배치·코드·스테이션 번호·링 크기) 미합의: 지금 DB에는 화면 개발용 가짜 데이터뿐");
        set(S2[48], "v2 씬 센서·태그, GX Works2 래더와 GX Simulator2 연결(MX Component 버전 확인)이 남음");
        set(S2[49], "이벤트를 셀·검사·박스 테이블로 옮기는 규칙과 수집기 배포 (스키마 06 · API 0.3, PR 검토 중)");
        set(S2[50], "결정과 확인이 필요한 것");
        set(S2[51], "데이터 쪽이 못 따라올 때 라인을 멈출지(누락 0) 계속 돌릴지(누락 감지만) 결정 필요, 멈추려면 래더 변경");
        set(S2[52], "v2 배치 위험 3건 반영 여부, 셀 전압 실측, 실습실 네트워크에서 서버 접속(SSH·Tailscale) " + GAP);

        set(S2[55], "중간 총평 (초안)");
        set(S2[56], "11/23 공정을 v2로 다시 짜면서, 배치가 바뀌어도 DB·SCADA·HMI가 흔들리지 않도록 스테이션 코드와 이벤트를 먼저 맞췄다.");
        set(S2[58], "PLC와 DB 사이 약속(메일박스)을 정하지 못해, DB 쪽은 가짜 PLC로 먼저 끝까지 시험했다. 합의되면 설정만 바꿔 붙일 수 있게 했다.");
        set(S2[60], "남은 기간에는 래더·씬과 수집기를 실제로 연결해 100셀을 흘리고, 계획서의 확인 기준을 숫자로 확인하는 것이 목표다.");
        deleteRange(s2, S2, 61, 70);

        // ===== drop the demo-video appendix =====
        f.getBodyText().getSectionList().remove(3);

        blankUnusedBins();
        HWPWriter.toFile(f, a[1]);
        System.out.println("wrote " + a[1]);
    }

    /** Replace only the text before the first control character in a paragraph that also holds controls. */
    static void replaceLeadingText(Paragraph p, String text) throws Exception {
        var t = p.getText();
        var chars = t.getCharList();
        int i = 0;
        while (i < chars.size() && chars.get(i).getType() == kr.dogfoot.hwplib.object.bodytext.paragraph.text.HWPCharType.Normal) i++;
        for (int k = 0; k < i; k++) chars.remove(0);
        int pos = 0;
        for (char ch : text.toCharArray()) {
            var nc = new kr.dogfoot.hwplib.object.bodytext.paragraph.text.HWPCharNormal(ch);
            chars.add(pos++, nc);
        }
        long cs = p.getCharShape().getPositonShapeIdPairList().get(0).getShapeId();
        p.deleteCharShape();
        p.createCharShape();
        p.getCharShape().addParaCharShape(0, cs);
        p.deleteLineSeg();
        p.deleteRangeTag();
        p.getHeader().setCharShapeCount(1);
        p.getHeader().setLineAlignCount(0);
        p.getHeader().setRangeTagCount(0);
        int count = 0;
        for (var c : chars) count += c.getCharSize();
        p.getHeader().setCharacterCount(count);
    }
}
