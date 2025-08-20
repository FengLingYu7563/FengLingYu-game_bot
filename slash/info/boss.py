import discord
from discord import app_commands
import pandas as pd
import os

# 設定 boss.csv 路徑
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "boss.csv")

def load_data():
    """讀取 CSV 檔案，返回 DataFrame"""
    if not os.path.exists(DATA_PATH):
        print(f"❌ 找不到檔案: {DATA_PATH}")
        return None
    try:
        df = pd.read_csv(DATA_PATH, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    except Exception: # 捕獲所有讀取錯誤，但不輸出訊息
        return None

    # 如果 '編號' 欄位不存在，直接返回 None
    if '編號' not in df.columns:
        return None
    
    # 嘗試將 '編號' 轉換為數字，無法轉換的會變成 NaN
    # errors='coerce' 是關鍵，它會將所有無法轉換為數字的值都變成 NaN
    df['temp_編號_numeric'] = pd.to_numeric(df['編號'], errors='coerce')
    
    # 然後只保留 'temp_編號_numeric' 不是 NaN 的行
    # 這會過濾掉所有非數字、空字串、或只有空格的編號
    df_filtered = df[df['temp_編號_numeric'].notna()].copy()
    
    # 移除我們為了篩選而創建的臨時列
    df_filtered = df_filtered.drop(columns=['temp_編號_numeric'])
    
    # 如果過濾後 DataFrame 為空 (代表沒有任何有效編號的資料)，則返回 None
    if df_filtered.empty:
        return None

    # --- 對篩選後的有效資料進行類型轉換 ---
    try:
        # 現在 '章節' 和 '編號' 欄位應該都是純數字（或已過濾掉非數字）
        # 所以可以直接安全地進行 astype(int) 轉換
        df_filtered["章節"] = df_filtered["章節"].astype(int)
        df_filtered["編號"] = df_filtered["編號"].astype(int).astype(str).str.replace(".0", "", regex=False)
        
    except Exception: # 捕獲所有轉換錯誤，但不輸出訊息
        return None
    
    return df_filtered

# 不許偷家
class RestrictedView(discord.ui.View):
    def __init__(self, original_interactor_id: int, data: pd.DataFrame, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.original_interactor_id = original_interactor_id
        self.data = data # 將完整的 DataFrame 傳遞下去，供後續下拉選單使用

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 檢查互動者是否是原始呼叫指令的使用者
        if interaction.user and interaction.user.id == self.original_interactor_id:
            return True
        else:
            # 如果不是原始互動者，發送一個臨時訊息告訴他們
            await interaction.response.send_message("這個選單只能由發起指令的使用者操作。", ephemeral=True)
            return False

    async def on_timeout(self):
        # 當 View 超時時，移除所有組件，讓選單無法再被操作
        if self.message: # 確保 message 已經被設定 (來自 send_message 或 edit_message)
            for item in self.children:
                item.disabled = True # 禁用所有互動組件
            await self.message.edit(content="選單已超時，無法再操作。", view=self)

class ChapterDropdown(discord.ui.Select):
    """章節選擇下拉選單"""
    def __init__(self):
        options = [
            discord.SelectOption(label="1-3章節", value="1-3"),
            discord.SelectOption(label="4-6章節", value="4-6"),
            discord.SelectOption(label="7-9章節", value="7-9"),
            discord.SelectOption(label="10-12章節", value="10-12"),
            discord.SelectOption(label="13-15章節", value="13-15"),
            # discord.SelectOption(label="16-18章節", value="16-18")
        ]
        super().__init__(placeholder="選擇章節範圍...", options=options)

    async def callback(self, interaction: discord.Interaction):
        chapter_range = self.values[0]
        data = self.view.data

        start_chapter, end_chapter = map(int, chapter_range.split('-'))
        
        bosses = data[(data['章節'] >= start_chapter) & (data['章節'] <= end_chapter)].copy()
            
        boss_dropdown = BossDropdown(bosses)
        view = discord.ui.View()
        view.add_item(boss_dropdown)
        await interaction.response.edit_message(content="請選擇 Boss：", view=view)

class BossDropdown(discord.ui.Select):
    """Boss 選擇下拉選單"""
    def __init__(self, bosses):
        options = [
            discord.SelectOption(
                label=f"{row['編號']}. {row['名稱']}",
                description=f"第{row['章節']}章 {row['名稱']} ({row['英文']})",
                value=row["名稱"]
            )
            for _, row in bosses.iterrows()
        ]
        super().__init__(placeholder="選擇 Boss...", options=options)
        self.bosses = bosses

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()  # 延遲回應
        boss_name = self.values[0]
        boss_info = self.bosses[self.bosses["名稱"] == boss_name].iloc[0]
        # 建立 Embed 來顯示資訊
        embed = discord.Embed(title=f" {(boss_info['編號'])}. 主線王：{boss_name} ( {boss_info['英文']} ) 的資訊", color=discord.Color.purple())
        
        # 放set_author(header)
        description_content = (
            f":cherry_blossom: 章節 : {boss_info['章節']}\n"
            f":cherry_blossom: 地點: {boss_info['地點']}\n"
            f":cherry_blossom: 需要主線嗎: {boss_info['需要主線']}"
        )
        embed.description = description_content
        
        embed.add_field(name=":maple_leaf: 等級 :maple_leaf:", value=boss_info['等級'], inline=False)
        embed.add_field(name=":maple_leaf: 屬性 :maple_leaf:", value=boss_info['屬性'], inline=False)
        embed.add_field(name="", value="", inline=False)
        # 使用 inline=True 來並排顯示
        embed.add_field(name="物防 P.Def", value=str(boss_info['物理防禦']), inline=True)
        embed.add_field(name="魔防 M.Def", value=str(boss_info['魔法防禦']), inline=True)
        embed.add_field(name="物理抗性 P.Res", value=boss_info['物理抗性'], inline=True)
        embed.add_field(name="", value="", inline=False)
        embed.add_field(name="魔法抗性 M.Res", value=boss_info['魔法抗性'], inline=True)
        embed.add_field(name="迴避 Flee", value=str(boss_info['迴避']), inline=True)
        embed.add_field(name="抗暴 Crt.Res", value=str(boss_info['抗暴']), inline=True)
        embed.add_field(name="", value="", inline=False)
        embed.add_field(name=":maple_leaf: 慣性變動率 Proration :maple_leaf:", value=boss_info['慣性變動率'], inline=False)
        embed.add_field(name="", value="", inline=False)
        # 有控制就加
        if pd.notna(boss_info['控制']):
            embed.add_field(name=":maple_leaf: 控制 FTS :maple_leaf:", value=boss_info['控制'], inline=False)
            embed.add_field(name="", value="", inline=False)
        # 有階段/模式就加
        if pd.notna(boss_info['階段/模式']):
            embed.add_field(name="", value="", inline=False)
            embed.add_field(name=":maple_leaf: 階段/模式 Phase :maple_leaf:", value=boss_info['階段/模式'], inline=False)
            embed.add_field(name="", value="", inline=False)
        # 有限傷就加
        if pd.notna(boss_info['限傷']):
            embed.add_field(name="", value="", inline=False)
            embed.add_field(name=":maple_leaf: 限傷 Notice :maple_leaf:", value=boss_info['限傷'], inline=False)
            embed.add_field(name="", value="", inline=False)
        # 有破位效果就加
        if pd.notna(boss_info['破位效果']):
            embed.add_field(name="", value="", inline=False)
            embed.add_field(name=":maple_leaf: 破位效果 Break Effect :maple_leaf:", value=boss_info['破位效果'], inline=False)
            embed.add_field(name="", value="", inline=False)
        # 有注意就加
        if pd.notna(boss_info['注意']):
            embed.add_field(name="", value="", inline=False)
            embed.add_field(name=":maple_leaf: 注意 Notice :maple_leaf:", value=boss_info['注意'], inline=False)
            embed.add_field(name="", value="", inline=False)
        embed.set_image(url=boss_info['img_url'])
        embed.set_footer(text=f"""✧*。 難度倍率 Difficulty 。*✧\nEASY = 0.1 x 防禦 | 迴避\nNORMAL = 1 x 防禦 | 迴避\nHARD = 2 x 防禦 | 迴避\nNIGHTMARE = 4 x 防禦 | 迴避\nULTIMATE = 6 x 防禦 | 迴避""")
        await interaction.edit_original_response(content="✅ 查詢結果：", embed=embed, view=None)


class InfoGroup(app_commands.Group):
    """定義 /info 指令群組"""
    @app_commands.command(name="boss", description="查詢 Boss 資料")
    async def boss(self, interaction: discord.Interaction):
        """當使用者輸入 /info boss，顯示 Boss 下拉式選單"""
        df = load_data()
        if df is None:
            await interaction.response.send_message("❌ 找不到 Boss 資料！", ephemeral=True)
            return

        chapter_dropdown = ChapterDropdown()
        view = discord.ui.View()
        view.add_item(chapter_dropdown)
        view.data = df
        await interaction.response.send_message("請選擇章節：", view=view)

info_group = InfoGroup(name="info", description="查詢遊戲資料")