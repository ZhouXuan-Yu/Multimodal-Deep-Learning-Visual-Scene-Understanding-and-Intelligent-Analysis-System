# EmailJS 配置说明（前端）

你现在看到的报错：

- `POST https://api.emailjs.com/api/v1.0/email/send 404 (Not Found)`
- `Account not found`

通常表示 **EmailJS Public Key 和 Service ID / Template ID 不属于同一个 EmailJS 账号**，或页面仍在使用旧的 Public Key。

## 需要配置的环境变量

本项目在 `ContactView.vue` 中通过 Vite 环境变量读取 EmailJS 配置：

- `VITE_EMAILJS_PUBLIC_KEY`
- `VITE_EMAILJS_SERVICE_ID`
- `VITE_EMAILJS_TEMPLATE_ID`
- `VITE_EMAILJS_RECEIVER_EMAIL`

示例见 `env.example`，建议你复制为 `.env.local`（不要提交到 git）。

## 正确获取 ID 的位置
Service ID  service_jbw13bs
模板ID: template_8721z3o
公钥 QX7oSAGgB_-cSoX9A
私钥 33aHkUfPabioxHh6H_cjG

- **Public Key**: EmailJS Dashboard → Account → API Keys（Public Key）
- **Service ID**: EmailJS Dashboard → Email Services → 选择你的服务 → Service ID
- **Template ID**: EmailJS Dashboard → Email Templates → 选择你的模板 → Template ID

## 安全注意事项（重要）

- **不要把 EmailJS Private Key/Secret 放到前端代码或任何前端 env 里**（任何用户都能在浏览器里看到）。
- 如果你已经把 Private Key 贴到公开位置（包括聊天记录、仓库、截图），建议你立刻在 EmailJS 后台 **重新生成/撤销**。

