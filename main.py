import os
import re
import discord
from discord.ext import commands

# =========================================================
# CONFIG
# =========================================================

# Đặt token mới vào biến môi trường DISCORD_TOKEN
TOKEN = os.getenv("MTU1MTE1MzQ3NDM5NjIyOTcwMg.GTH7W4.j1o9DVE7gxNykWFxlJnbEqh0lSp-wU_DlbRrxw", "")

PREFIX = "!"
TICKET_CATEGORY_NAME = "🎫・TICKETS"

# Sản phẩm
PRODUCTS = {
    "toi_uu_basic": {
        "name": "⚙️ Tối ưu máy BASIC",
        "price": 50000,
        "description": "Gói tối ưu cơ bản cho PC."
    },
    "toi_uu_pro": {
        "name": "🚀 Tối ưu máy PRO",
        "price": 100000,
        "description": "Gói tối ưu nâng cao cho PC."
    },
    "toi_uu_vip": {
        "name": "👑 Tối ưu máy VIP",
        "price": 150000,
        "description": "Gói tối ưu VIP."
    },
    "reg_sensi": {
        "name": "🎯 Reg Sensi FF PC",
        "price": 70000,
        "description": "Dịch vụ reg sensi FF PC."
    }
}


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents
)


# =========================================================
# UTILS
# =========================================================

def money(v: int) -> str:
    return f"{v:,}".replace(",", ".") + "đ"


def safe_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name[:70].strip("-") or "user"


def can_manage_ticket(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return perms.administrator or perms.manage_channels


async def get_or_create_category(guild: discord.Guild):
    category = discord.utils.get(
        guild.categories,
        name=TICKET_CATEGORY_NAME
    )

    if category:
        return category

    return await guild.create_category(
        TICKET_CATEGORY_NAME,
        reason="Tạo category ticket cho shop"
    )


def find_open_ticket(guild: discord.Guild, user_id: int):
    category = discord.utils.get(
        guild.categories,
        name=TICKET_CATEGORY_NAME
    )

    if not category:
        return None

    for channel in category.text_channels:
        if channel.topic and f"ticket_owner:{user_id}" in channel.topic:
            return channel

    return None


# =========================================================
# SELECT MENU
# =========================================================

class ProductSelect(discord.ui.Select):

    def __init__(self):
        options = []

        for key, product in PRODUCTS.items():
            options.append(
                discord.SelectOption(
                    label=product["name"][:100],
                    description=(
                        f"{money(product['price'])} • "
                        f"{product['description']}"
                    )[:100],
                    value=key
                )
            )

        super().__init__(
            placeholder="🛒 Chọn sản phẩm bạn muốn mua...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        product_id = self.values[0]
        product = PRODUCTS[product_id]

        existing = find_open_ticket(
            interaction.guild,
            interaction.user.id
        )

        if existing:
            await interaction.response.send_message(
                f"❌ Bạn đã có ticket: {existing.mention}",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛍️ Đơn hàng",
            description=(
                f"**Sản phẩm:** {product['name']}\n"
                f"**Giá:** `{money(product['price'])}`\n\n"
                "Bấm **Đặt hàng** để bot tạo ticket riêng cho bạn."
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=OrderConfirmView(product_id),
            ephemeral=True
        )


class ProductView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ProductSelect())


# =========================================================
# ORDER CONFIRM
# =========================================================

class OrderConfirmView(discord.ui.View):

    def __init__(self, product_id: str):
        super().__init__(timeout=300)
        self.product_id = product_id

    @discord.ui.button(
        label="🛒 Đặt hàng",
        style=discord.ButtonStyle.green
    )
    async def order_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild
        user = interaction.user
        product = PRODUCTS[self.product_id]

        existing = find_open_ticket(
            guild,
            user.id
        )

        if existing:
            await interaction.response.send_message(
                f"❌ Bạn đã có ticket: {existing.mention}",
                ephemeral=True
            )
            return

        category = await get_or_create_category(guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        # Admin / Manage Channels có thể vào
        for member in guild.members:
            if member.bot:
                continue

            if can_manage_ticket(member):
                overwrites[member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True
                )

        channel_name = (
            f"ticket-{safe_name(user.name)}-{user.id}"
        )

        channel = await guild.create_text_channel(
            name=channel_name[:100],
            category=category,
            overwrites=overwrites,
            topic=(
                f"ticket_owner:{user.id} "
                f"| product:{self.product_id} "
                f"| price:{product['price']}"
            ),
            reason="Khách tạo đơn hàng"
        )

        embed = discord.Embed(
            title="🎫 TICKET ĐƠN HÀNG",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 Khách hàng",
            value=user.mention,
            inline=False
        )

        embed.add_field(
            name="🛍️ Sản phẩm",
            value=product["name"],
            inline=False
        )

        embed.add_field(
            name="💰 Giá",
            value=money(product["price"]),
            inline=False
        )

        embed.set_footer(
            text="Admin sẽ vào ticket để xử lý đơn hàng."
        )

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=TicketView()
        )

        await interaction.response.send_message(
            f"✅ Đã tạo ticket: {channel.mention}",
            ephemeral=True
        )


# =========================================================
# TICKET BUTTONS
# =========================================================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Đóng ticket",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.user

        owner_id = None

        if interaction.channel.topic:
            match = re.search(
                r"ticket_owner:(\d+)",
                interaction.channel.topic
            )

            if match:
                owner_id = int(match.group(1))

        allowed = (
            owner_id == member.id
            or can_manage_ticket(member)
        )

        if not allowed:
            await interaction.response.send_message(
                "❌ Bạn không có quyền đóng ticket này.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket sẽ được đóng...",
            ephemeral=True
        )

        await interaction.channel.delete(
            reason="Đóng ticket"
        )


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():

    print("=" * 50)
    print(f"BOT: {bot.user}")
    print(f"ID : {bot.user.id}")
    print("STATUS: ONLINE")
    print("=" * 50)

    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print("Sync error:", e)

    # Persistent button
    bot.add_view(TicketView())


# =========================================================
# SLASH COMMAND /shop
# =========================================================

@bot.tree.command(
    name="shop",
    description="Mở cửa hàng"
)
async def shop(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛒 SHOP DỊCH VỤ",
        description=(
            "Chọn sản phẩm bạn muốn mua ở menu bên dưới.\n\n"
            "Bot sẽ tạo **ticket riêng** cho đơn hàng của bạn."
        ),
        color=discord.Color.blurple()
    )

    for product in PRODUCTS.values():
        embed.add_field(
            name=product["name"],
            value=f"💰 **{money(product['price'])}**",
            inline=False
        )

    embed.set_footer(
        text="Chọn sản phẩm để tiếp tục."
    )

    await interaction.response.send_message(
        embed=embed,
        view=ProductView()
    )


# =========================================================
# PREFIX COMMAND !shop
# =========================================================

@bot.command()
async def shopcmd(ctx):
    embed = discord.Embed(
        title="🛒 SHOP DỊCH VỤ",
        description="Chọn sản phẩm bên dưới.",
        color=discord.Color.blurple()
    )

    for product in PRODUCTS.values():
        embed.add_field(
            name=product["name"],
            value=f"💰 **{money(product['price'])}**",
            inline=False
        )

    await ctx.send(
        embed=embed,
        view=ProductView()
    )


# =========================================================
# RUN
# =========================================================

if not TOKEN:
    print(
        "❌ Chưa có DISCORD_TOKEN.\n"
        "Hãy đặt token mới vào biến môi trường DISCORD_TOKEN."
    )
else:
    bot.run(TOKEN)
