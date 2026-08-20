<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetScope Pro - AI Predictor Engine</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background-color: #0b0f19;
            color: #ffffff;
            padding: 16px;
            display: flex;
            justify-content: center;
        }
        .app-container {
            width: 100%;
            max-width: 440px;
        }
        /* Top Banner */
        .top-banner {
            background: rgba(225, 29, 72, 0.1);
            border: 1px solid rgba(225, 29, 72, 0.3);
            border-radius: 12px;
            padding: 12px;
            font-size: 11px;
            color: #f43f5e;
            text-align: center;
            margin-bottom: 16px;
            line-height: 1.4;
        }
        /* Scanner Box */
        .scanner-box {
            background: #111827;
            border: 2px dashed #374151;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            margin-bottom: 16px;
        }
        .preview-mini-ticket {
            background: #ffffff;
            border-radius: 8px;
            width: 140px;
            margin: 0 auto 15px auto;
            padding: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }
        .mini-row {
            font-size: 8px;
            color: #333;
            display: flex;
            justify-content: space-between;
            padding: 3px 0;
            border-bottom: 1px solid #eee;
        }
        .btn-analyze {
            background: linear-gradient(135deg, #e11d48, #be123c);
            color: white;
            border: none;
            width: 100%;
            padding: 14px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(225, 29, 72, 0.4);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 12px 6px;
            text-align: center;
        }
        .stat-label {
            font-size: 9px;
            color: #9ca3af;
            text-transform: uppercase;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }
        .stat-value {
            font-size: 14px;
            font-weight: bold;
            color: #34d399;
        }
        /* Match Card */
        .match-card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
            position: relative;
        }
        .match-card.border-blue { border-left: 4px solid #3b82f6; }
        .match-card.border-red { border-left: 4px solid #e11d48; }

        .match-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .league-tag {
            font-size: 10px;
            font-weight: bold;
            color: #fbbf24;
            text-transform: uppercase;
        }
        .accuracy-tag {
            font-size: 10px;
            color: #34d399;
        }
        .badge-prediction {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .badge-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .badge-green { background: rgba(16, 185, 129, 0.2); color: #34d399; }

        .teams-title {
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 10px;
            letter-spacing: 0.3px;
        }
        .safest-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            font-size: 12px;
        }
        .safest-label { color: #9ca3af; font-size: 10px; text-transform: uppercase; }
        .safest-pick-val { color: #ffffff; font-weight: bold; }
        .odds-badge {
            background: #1f2937;
            border: 1px solid #374151;
            padding: 6px 10px;
            border-radius: 8px;
            text-align: center;
            min-width: 75px;
        }
        .odds-badge .o-label { font-size: 9px; color: #9ca3af; }
        .odds-badge .o-val { font-size: 13px; font-weight: bold; color: #fbbf24; }

        /* Odds Options Grid */
        .odds-options {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }
        .odd-opt {
            background: #0b0f19;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 8px;
            text-align: center;
        }
        .odd-opt .opt-name { font-size: 9px; color: #9ca3af; margin-bottom: 2px; }
        .odd-opt .opt-val { font-size: 12px; font-weight: bold; color: #d1d5db; }
        
        /* Highlighted Selected Odd */
        .odd-opt.selected {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid #10b981;
        }
        .odd-opt.selected .opt-val { color: #34d399; }

        .footer-note {
            text-align: center;
            font-size: 9px;
            color: #6b7280;
            margin-top: 20px;
            padding-bottom: 10px;
        }
    </style>
</head>
<body>

<div class="app-container">

    <!-- Top Banner -->
    <div class="top-banner">
        ⚽ <strong>Instant Virtual Multi-League OCR:</strong> Position-aware spatial scanner detecting heavy favorites & lowest risk winning odds. 10 Rounds limit active.
    </div>

    <!-- Scanner / Re-Analyze Box -->
    <div class="scanner-box">
        <div class="preview-mini-ticket">
            <div class="mini-row"><span>FUL vs BRE</span><span>1.96</span></div>
            <div class="mini-row"><span>HUL vs MUN</span><span>1.95</span></div>
            <div class="mini-row"><span>BHA vs BOU</span><span>2.05</span></div>
        </div>
        <button class="btn-analyze">🔄 Re-Analyze Ticket (2 Best Picks)</button>
    </div>

    <!-- Stats Bar -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Win Rate</div>
            <div class="stat-value">99.8%</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Picks Decoded</div>
            <div class="stat-value">2</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Status</div>
            <div class="stat-value" style="font-size: 11px; padding-top:2px;">100% Matched</div>
        </div>
    </div>

    <!-- Match 1: Everton vs Arsenal -->
    <div class="match-card border-blue">
        <div class="match-header">
            <span class="league-tag">🏆 English League #1</span>
            <span class="accuracy-tag">🛡️ Win Accuracy: 99.2%</span>
        </div>
        <div>
            <span class="badge-prediction badge-blue">AWAY WIN (2)</span>
        </div>
        <div class="teams-title">EVE (Everton) vs ARS (Arsenal)</div>
        
        <div class="safest-box">
            <div>
                <div class="safest-label">Safest Pick</div>
                <div class="safest-pick-val">👉 Arsenal (Away Win (2))</div>
            </div>
            <div class="odds-badge">
                <div class="o-label">Ticket Odds</div>
                <div class="o-val">@ 2.07</div>
            </div>
        </div>

        <div class="odds-options">
            <div class="odd-opt">
                <div class="opt-name">1 (Home)</div>
                <div class="opt-val">3.68</div>
            </div>
            <div class="odd-opt">
                <div class="opt-name">X (Draw)</div>
                <div class="opt-val">3.20</div>
            </div>
            <div class="odd-opt selected">
                <div class="opt-name">2 (Away)</div>
                <div class="opt-val">2.07</div>
            </div>
        </div>
    </div>

    <!-- Match 2: Brighton vs Bournemouth -->
    <div class="match-card border-red">
        <div class="match-header">
            <span class="league-tag">🏆 English League #2</span>
            <span class="accuracy-tag">🛡️ Win Accuracy: 99.2%</span>
        </div>
        <div>
            <span class="badge-prediction badge-green">HOME WIN (1)</span>
        </div>
        <div class="teams-title">BHA (Brighton) vs BOU (Bournemouth)</div>
        
        <div class="safest-box">
            <div>
                <div class="safest-label">Safest Pick</div>
                <div class="safest-pick-val">👉 Brighton (Home Win (1))</div>
            </div>
            <div class="odds-badge">
                <div class="o-label">Ticket Odds</div>
                <div class="o-val">@ 2.05</div>
            </div>
        </div>

        <div class="odds-options">
            <div class="odd-opt selected">
                <div class="opt-name">1 (Home)</div>
                <div class="opt-val">2.05</div>
            </div>
            <div class="odd-opt">
                <div class="opt-name">X (Draw)</div>
                <div class="opt-val">3.95</div>
            </div>
            <div class="odd-opt">
                <div class="opt-name">2 (Away)</div>
                <div class="opt-val">3.23</div>
            </div>
        </div>
    </div>

    <div class="footer-note">
        © 2026 BetScope Pro AI Engine. 100% Anti-Detection Safe.
    </div>

</div>

</body>
</html>
